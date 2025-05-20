from rest_framework import serializers

class LeaveSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    employee_id = serializers.CharField()
    employee_name = serializers.CharField()
    leave_type = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(required=False)
    status = serializers.CharField(required=False, default='Pending')
    created_at = serializers.DateTimeField(required=False)
