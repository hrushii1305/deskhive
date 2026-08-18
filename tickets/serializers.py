from rest_framework import serializers
from .models import Ticket, Comment

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'organization', 'assigned_to', 'requester',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'assigned_to', 'requester',
            'created_at', 'updated_at',
        ]
        
        
class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ['id', 'ticket', 'author', 'body', 'created_at']
        read_only_fields = ['id', 'ticket', 'author', 'created_at']