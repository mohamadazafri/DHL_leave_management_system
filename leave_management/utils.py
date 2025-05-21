# leave_management/utils.py
import pdb
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime


def send_status_email(leave_data, status):
    start_date = leave_data.get('start_date')
    end_date = leave_data.get('end_date')

    if isinstance(start_date, str):
        try:
            start_date = datetime.fromisoformat(start_date)
        except Exception:
            start_date = None

    if isinstance(end_date, str):
        try:
            end_date = datetime.fromisoformat(end_date)
        except Exception:
            end_date = None

    # Now you can safely use strftime
    from_str = start_date.strftime('%d %b, %Y') if start_date else '-'
    to_str = end_date.strftime('%d %b, %Y') if end_date else '-'


    """Send email notification when leave status changes"""
    subject = f"Leave Application Status Update - {status}"
    
    message = f"""
Hello Admin,

A leave application status has been updated:

Employee: {leave_data.get('employee_name')} ({leave_data.get('employee_id')})
Department: {leave_data.get('department')}
Leave Type: {leave_data.get('leave_type')}
From: {from_str}
To: {to_str}
Status: {status}

This is an automated notification from the DHL Leave Management System.
    """
    
    # email_from = settings.EMAIL_HOST_USER
    # recipient_list = [settings.ADMIN_EMAIL]
    
    # send_mail(subject, message, email_from, recipient_list)
    
    return True

def send_bulk_entry_notification(successful_count, failed_count):
    """Send notification when UiPath adds bulk entries"""
    subject = "Data Entry Status Update"
    
    message = f"""
Hello Admin,

Bulk data entry has been completed via the UiPath integration.

Total entries processed: {successful_count + failed_count}
Successful entries: {successful_count}
Failed entries (duplicates): {failed_count}
Date and Time: {datetime.now().strftime('%d %b, %Y %H:%M:%S')}

This is an automated notification from the DHL Leave Management System.
    """
    
    # email_from = settings.EMAIL_HOST_USER
    recipient_list = [settings.ADMIN_EMAIL]
    
    # send_mail(subject, message, email_from, recipient_list)
    
    return True