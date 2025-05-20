from bson.json_util import dumps
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from dotenv import load_dotenv  
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import LeaveApplication
from .serializers import LeaveSerializer
from .utils import send_status_email, send_bulk_entry_notification
import io
import json
import os
import pandas as pd
import pymongo
import requests
import aiohttp
import asyncio
import pdb
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from collections import defaultdict
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# MongoDB connection
mongo_client = pymongo.MongoClient(os.getenv('MONGODB_HOST'))
mongo_db = mongo_client[os.getenv('MONGODB_NAME')]
leave_collection = mongo_db['leave_applications']

# Create your views here.

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'leave_management/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get status filter
        status_filter = self.request.GET.get('status', '')
        
        # Prepare filter query
        filter_query = {}
        if status_filter:
            filter_query['status'] = status_filter
        
        # Get leave applications
        leaves = list(leave_collection.find(filter_query).sort('created_at', -1))
        
        # Convert ObjectId to string for each leave
        for leave in leaves:
            leave['id'] = str(leave['_id'])
        
        # Count by status
        total_leaves = leave_collection.count_documents({})
        pending_leaves = leave_collection.count_documents({'status': 'Pending'})
        approved_leaves = leave_collection.count_documents({'status': 'Approved'})
        
        # Get leave types distribution for chart
        pipeline = [
            {'$group': {'_id': '$leave_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        leave_types_agg = list(leave_collection.aggregate(pipeline))
        
        leave_types = []
        leave_counts = []
        
        for item in leave_types_agg:
            leave_types.append(item['_id'])
            leave_counts.append(item['count'])
            
        for leave in leaves:
            for field in ['start_date', 'end_date']:
                if field in leave and isinstance(leave[field], str):
                    try:
                        leave[field] = datetime.fromisoformat(leave[field])
                    except Exception:
                        leave[field] = None
        
        context.update({
            'leaves': leaves,
            'total_leaves': total_leaves,
            'pending_leaves': pending_leaves,
            'approved_leaves': approved_leaves,
            'status': status_filter,
            'leave_types': json.dumps(leave_types),
            'leave_counts': json.dumps(leave_counts)
        })
        
        return context

class DashboardV2View(TemplateView):
    template_name = 'leave_management/dashboard_v2.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        leaves = list(leave_collection.find({}))
        for leave in leaves:
            for field in ['start_date', 'end_date']:
                if field in leave and isinstance(leave[field], str):
                    try:
                        leave[field] = datetime.fromisoformat(leave[field])
                    except Exception:
                        leave[field] = None
        # Prepare events for FullCalendar
        events = []
        for leave in leaves:
            if leave.get('start_date') and leave.get('end_date'):
                events.append({
                    "title": f"{leave['employee_name']} ({leave['leave_type']})",
                    "start": leave['start_date'].strftime("%Y-%m-%d"),
                    "end": (leave['end_date'] + timedelta(days=1)).strftime("%Y-%m-%d"),  # FullCalendar's end is exclusive
                    "color": "#f59e42" if leave.get('status') == "Pending" else "#34d399" if leave.get('status') == "Approved" else "#f87171"
                })
        context['calendar_events'] = json.dumps(events)
        return context

class LeaveFormView(TemplateView):
    template_name = 'leave_management/leave_form.html'
    
    def post(self, request, *args, **kwargs):
        # Get form data
        employee_id = request.POST.get('employee_id')
        employee_name = request.POST.get('employee_name')
        leave_type = request.POST.get('leave_type')
        department = request.POST.get('department')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        
        # Convert string dates to datetime objects
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Create leave application document
        leave_data = {
            'employee_id': employee_id,
            'employee_name': employee_name,
            'leave_type': leave_type,
            'department': department,
            'start_date': start_date,
            'end_date': end_date,
            'reason': reason,
            'status': 'Pending',
            'created_at': datetime.now()
        }
        
        # Insert into MongoDB
        leave_collection.insert_one(leave_data)
        
        # Return success message
        context = self.get_context_data(**kwargs)
        context['success_message'] = 'Leave application submitted successfully!'
        return render(request, self.template_name, context)

class UpdateLeaveStatusView(TemplateView):
    def post(self, request, leave_id, *args, **kwargs):
        status = request.POST.get('status')
        
        if status:
            # First get the leave data
            leave_data = leave_collection.find_one({'_id': ObjectId(leave_id)})
            
            # Update the status
            leave_collection.update_one(
                {'_id': ObjectId(leave_id)},
                {'$set': {'status': status}}
            )
            
            # Send email notification
            if leave_data:
                send_status_email(leave_data, status)
        
        return redirect('dashboard')

class LeaveListView(APIView):
    def get(self, request):
        leaves = list(leave_collection.find())
        
        # Convert ObjectId to string
        for leave in leaves:
            leave['id'] = str(leave['_id'])
            del leave['_id']
        
        return Response(leaves)
    
    def post(self, request):
        data = request.data
        
        # Convert string dates to datetime objects if they are strings
        if isinstance(data.get('start_date'), str):
            data['start_date'] = datetime.strptime(data['start_date'], '%Y-%m-%d')
        
        if isinstance(data.get('end_date'), str):
            data['end_date'] = datetime.strptime(data['end_date'], '%Y-%m-%d')
        
        # Add created_at timestamp and default status
        data['created_at'] = datetime.now()
        data['status'] = 'Pending'
        
        # Insert into MongoDB
        result = leave_collection.insert_one(data)
        
        return Response({
            'status': 'success',
            'leave_id': str(result.inserted_id)
        }, status=status.HTTP_201_CREATED)

class LeaveDetailView(APIView):
    def get_object(self, pk):
        try:
            return leave_collection.find_one({'_id': ObjectId(pk)})
        except:
            return None
    
    def get(self, request, pk):
        leave = self.get_object(pk)
        if leave:
            leave['id'] = str(leave['_id'])
            del leave['_id']
            return Response(leave)
        return Response({'error': 'Leave not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, pk):
        status_update = request.data.get('status')
        
        if status_update:
            # First get the leave data
            leave_data = self.get_object(pk)
            
            result = leave_collection.update_one(
                {'_id': ObjectId(pk)},
                {'$set': {'status': status_update}}
            )
            
            if result.modified_count and leave_data:
                # Send email notification
                send_status_email(leave_data, status_update)
                return Response({'status': 'updated'})
        
        return Response({'error': 'Failed to update'}, status=status.HTTP_400_BAD_REQUEST)

class BulkLeaveUploadView(APIView):
    def post(self, request):
        try:
            leaves_data = request.data.get('leaves', [])
            
            if not leaves_data or not isinstance(leaves_data, list):
                return Response({
                    'error': 'Invalid data format. Expected a list of leave entries.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            inserted_ids = []
            
            for leave in leaves_data:
                # Convert string dates to datetime objects if they are strings
                if isinstance(leave.get('start_date'), str):
                    leave['start_date'] = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                
                if isinstance(leave.get('end_date'), str):
                    leave['end_date'] = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                
                # Add created_at timestamp and default status if not provided
                leave['created_at'] = datetime.now()
                if 'status' not in leave:
                    leave['status'] = 'Pending'
                
                # Insert into MongoDB
                result = leave_collection.insert_one(leave)
                inserted_ids.append(str(result.inserted_id))
            
            # Send email notification about bulk upload
            send_bulk_entry_notification(len(inserted_ids))
            
            return Response({
                'status': 'success',
                'message': f'Successfully uploaded {len(inserted_ids)} leave applications',
                'inserted_ids': inserted_ids
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BulkUploadView(TemplateView):
    template_name = 'leave_management/bulk_upload.html'
    
    def post(self, request, *args, **kwargs):
        try:
            upload_type = request.POST.get('upload_type')
            if upload_type == 'excel':
                excel_file = request.FILES.get('excel_file')
                if not excel_file:
                    context = self.get_context_data(**kwargs)
                    context['message'] = 'No file uploaded.'
                    context['message_type'] = 'red'
                    return render(request, self.template_name, context)
                df = pd.read_excel(excel_file)
            elif upload_type == 'sheets':
                sheets_url = request.POST.get('sheets_url')
                if not sheets_url:
                    context = self.get_context_data(**kwargs)
                    context['message'] = 'No Google Sheets URL provided.'
                    context['message_type'] = 'red'
                    return render(request, self.template_name, context)
                try:
                    api_endpoint = "https://cloud.uipath.com/mohamadazafri/DefaultTenant/orchestrator_/t/90df9974-3ce0-4751-923e-b6aeb3e49747/readexcel?in_SheetURL=" + sheets_url
                    response = requests.get(
                        api_endpoint,
                        params={'sheet_url': sheets_url},
                        headers={
                            'Authorization': f'Bearer {settings.UIPATH_TOKEN}',  
                        }
                    )
                    if response.status_code != 200:
                        raise Exception(f'API Error: {response.text}')
                    data = response.json()
                    df = pd.DataFrame(data['dtSheet'])
                except requests.RequestException as e:
                    context = self.get_context_data(**kwargs)
                    context['message'] = f'Error accessing Google Sheet API: {str(e)}'
                    context['message_type'] = 'red'
                    return render(request, self.template_name, context)
                except Exception as e:
                    context = self.get_context_data(**kwargs)
                    context['message'] = f'Error processing Google Sheet data: {str(e)}'
                    context['message_type'] = 'red'
                    return render(request, self.template_name, context)
            else:
                context = self.get_context_data(**kwargs)
                context['message'] = 'Invalid upload type.'
                context['message_type'] = 'red'
                return render(request, self.template_name, context)

            # Clean and prepare DataFrame
            df = df.rename(columns={
                'Employee Name': 'Employee_Name',
                'Staff ID': 'Staff_ID',
                'Leave Type': 'Leave_Type',
                'Start Date': 'Start_Date',
                'End Date': 'End_Date',
                'Status': 'Status',
            })
            df = df.dropna(subset=['Employee_Name', 'Staff_ID', 'Leave_Type', 'Start_Date', 'End_Date'])

            # Find duplicates within the uploaded data
            duplicate_mask = df.duplicated(subset=['Staff_ID', 'Start_Date'], keep=False)
            duplicate_df = df[duplicate_mask]
            unique_df = df[~duplicate_mask]

            # Process successful entries
            successful_entries = []
            for entry in unique_df.to_dict('records'):
                leave = {
                    'employee_id': str(entry['Staff_ID']),
                    'employee_name': str(entry['Employee_Name']),
                    'leave_type': str(entry['Leave_Type']),
                    'start_date': entry['Start_Date'],
                    'end_date': entry['End_Date'],
                    'status': str(entry.get('Status', 'Pending')),
                    'created_at': datetime.now()
                }
                result = leave_collection.insert_one(leave)
                successful_entries.append(leave)

            # Group failed entries by employee and start date
            grouped_failed_entries = []
            for _, group in duplicate_df.groupby(['Staff_ID', 'Start_Date']):
                entries = []
                for entry in group.to_dict('records'):
                    entries.append({
                        'employee_id': str(entry['Staff_ID']),
                        'employee_name': str(entry['Employee_Name']),
                        'leave_type': str(entry['Leave_Type']),
                        'start_date': pd.to_datetime(entry['Start_Date']).strftime('%Y-%m-%d'),
                        'end_date': pd.to_datetime(entry['End_Date']).strftime('%Y-%m-%d'),
                        'status': str(entry.get('Status', 'Pending'))
                    })
                grouped_failed_entries.append({
                    'staff_id': str(group['Staff_ID'].iloc[0]),
                    'start_date': pd.to_datetime(group['Start_Date'].iloc[0]).strftime('%Y-%m-%d'),
                    'entries': entries
                })

            # Send notification about successful uploads
            send_bulk_entry_notification(len(successful_entries), len(duplicate_df))

            # Render the upload result page
            return render(request, 'leave_management/upload_result.html', {
                'successful_entries': successful_entries,
                'grouped_failed_entries': grouped_failed_entries,
                'successful_count': len(successful_entries),
                'failed_count': len(duplicate_df)
            })

        except Exception as e:
            context = self.get_context_data(**kwargs)
            context['message'] = f'Error: {str(e)}'
            context['message_type'] = 'red'
            print(f"Exception details: {str(e)}")
            return render(request, self.template_name, context)
    
class LeaveApplicationsView(TemplateView):
    template_name = 'leave_management/leave_applications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        status = self.request.GET.get('status', '')
        filter_query = {}
        if status:
            filter_query['status'] = status
        leaves = list(leave_collection.find(filter_query).sort('created_at', -1))
        for leave in leaves:
            leave['id'] = str(leave['_id'])
            for field in ['start_date', 'end_date']:
                if field in leave and isinstance(leave[field], str):
                    try:
                        leave[field] = datetime.fromisoformat(leave[field])
                    except Exception:
                        leave[field] = None
        # Pagination
        page_number = self.request.GET.get('page', 1)
        paginator = Paginator(leaves, 15)
        page_obj = paginator.get_page(page_number)
        context['page_obj'] = page_obj
        context['leaves'] = page_obj.object_list
        context['paginator'] = paginator
        context['request'] = self.request
        return context

@csrf_protect
@never_cache
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Simple check for admin credentials
        if username == 'admin' and password == 'admin':
            # Create a simple user object
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(username='admin')
            except User.DoesNotExist:
                # Create admin user if it doesn't exist
                user = User.objects.create_user(
                    username='admin',
                    password='admin',
                    is_staff=True,
                    is_superuser=True
                )
            
            # Log the user in
            login(request, user)
            
            # Redirect to dashboard
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'registration/login.html')

class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return redirect('login')

class ProcessDuplicatesView(View):
    def get(self, request):
        try:
            # Parse form data from GET parameters
            selected_entries = {}
            for key in request.GET:
                if key.startswith('select-entry-'):
                    group_idx = key.replace('select-entry-', '')
                    selected_entries[group_idx] = request.GET[key]
            
            # Get grouped duplicates from session
            duplicate_data = request.session.get('duplicate_data', [])
            grouped_duplicates = group_duplicates(duplicate_data)
            
            saved_count = 0
            for group_idx, entry_idx in selected_entries.items():
                group_idx = int(group_idx)
                entry_idx = int(entry_idx)
                group = grouped_duplicates[group_idx]
                entry = group['entries'][entry_idx]
                leave_data = {
                    'employee_id': entry['Staff_ID'],
                    'employee_name': entry['Employee_Name'],
                    'leave_type': entry['Leave_Type'],
                    'start_date': entry['Start_Date'],
                    'end_date': entry['End_Date'],
                    'status': entry['Status'],
                    'created_at': datetime.now()
                }
                leave_collection.insert_one(leave_data)
                saved_count += 1
            
            # Clear the duplicate data from session after processing
            if 'duplicate_data' in request.session:
                del request.session['duplicate_data']
            
            # Redirect to bulk upload with success message
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(reverse('bulk_upload') + '?success=1')
            
        except Exception as e:
            # Redirect to bulk upload with error message
            from django.urls import reverse
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(reverse('bulk_upload') + f'?error={str(e)}')

def group_duplicates(duplicate_data):
    grouped = defaultdict(list)
    for entry in duplicate_data:
        # Use tuple of (Staff_ID, Start_Date) as the group key
        key = (entry['Staff_ID'], entry['Start_Date'])
        grouped[key].append(entry)
    # Convert to a list of dicts for template
    grouped_list = []
    for (staff_id, start_date), entries in grouped.items():
        grouped_list.append({
            'staff_id': staff_id,
            'start_date': start_date,
            'entries': entries,
            'employee_name': entries[0]['Employee_Name'] if entries else ''
        })
    return grouped_list

class DuplicateReviewView(TemplateView):
    template_name = 'leave_management/duplicate_review.html'

    def get(self, request, *args, **kwargs):
        duplicate_data = request.session.get('duplicate_data', [])
        grouped_duplicates = group_duplicates(duplicate_data)
        context = {'grouped_duplicates': grouped_duplicates}
        return render(request, self.template_name, context)

    
