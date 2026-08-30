from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from organizations.models import Organization
from .models import Member
from django.utils.text import slugify

class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    name = serializers.CharField()
    organization_name = serializers.CharField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            # 1. create the login account (password hashed by create_user)
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data['email'],
            )
            # 2. create their new organization with a unique slug
            base_slug = slugify(validated_data['organization_name'])
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            org = Organization.objects.create(
                name=validated_data['organization_name'],
                slug=slug,
            )
            # 3. create their Member profile as OWNER, linked to both
            member = Member.objects.create(
                user=user,
                organization=org,
                name=validated_data['name'],
                email=validated_data['email'],
                role='owner',
            )
        return member
    
    
class CustomerRegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    name = serializers.CharField()
    organization_id = serializers.IntegerField()
    
    def validate_email(self, value):
            if Member.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already registered.")
            return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_organization_id(self, value):
        # the org they want to join must exist and be active
        if not Organization.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Organization not found.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data['email'],
            )
            org = Organization.objects.get(id=validated_data['organization_id'])
            member = Member.objects.create(
                user=user,
                organization=org,
                name=validated_data['name'],
                email=validated_data['email'],
                role='customer',        # ← FORCED server-side, never from the client
            )
        return member
    
    
    
class AgentJoinRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField()
    name = serializers.CharField()
    organization_id = serializers.IntegerField()
    
    def validate_email(self, value):
            if Member.objects.filter(email=value).exists():
                raise serializers.ValidationError("Email already registered.")
            return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_organization_id(self, value):
        if not Organization.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Organization not found.")
        return value

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data['username'],
                password=validated_data['password'],
                email=validated_data['email'],
            )
            org = Organization.objects.get(id=validated_data['organization_id'])
            member = Member.objects.create(
                user=user,
                organization=org,
                name=validated_data['name'],
                email=validated_data['email'],
                role='agent',           # forced: this is an agent request
                status='pending',       # forced: must be approved by the owner
            )
        return member
    
class PendingAgentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'role', 'status', 'created_at']
        read_only_fields = fields
        
        
class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = ['id', 'name', 'email', 'role', 'status']
        read_only_fields = fields