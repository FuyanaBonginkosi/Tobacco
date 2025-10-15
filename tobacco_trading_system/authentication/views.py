from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import json
import secrets
import uuid

from .models import User, UserProfile, QRToken, EncryptedData, UserSession, SecurityLog
from utils.qr_code import qr_manager


def login_view(request):
    """Enhanced login with security features"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        try:
            user = User.objects.get(username=username)
            
            # Check if account is locked
            if not user.can_login():
                messages.error(request, 'Account is temporarily locked due to multiple failed login attempts.')
                log_security_event(user, 'LOGIN_FAILED', 'Account locked', ip_address, user_agent, severity='HIGH')
                return render(request, 'authentication/login.html')
            
            # Authenticate
            authenticated_user = authenticate(request, username=username, password=password)
            
            if authenticated_user:
                # Successful login
                login(request, authenticated_user)
                
                # Set session expiry
                if not remember_me:
                    request.session.set_expiry(0)  # Session expires when browser closes
                else:
                    request.session.set_expiry(1209600)  # 2 weeks
                
                # Record successful login
                user.record_login_attempt(success=True, ip_address=ip_address, device_info=user_agent)
                
                # Create session record
                UserSession.objects.create(
                    user=user,
                    session_key=request.session.session_key,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    device_type=get_device_type(user_agent),
                    browser_info=get_browser_info(user_agent)
                )
                
                # Log security event
                log_security_event(user, 'LOGIN_SUCCESS', 'User logged in successfully', ip_address, user_agent)
                
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect based on user type
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                elif user.is_timb_staff:
                    return redirect('timb_dashboard:dashboard')
                elif user.is_merchant:
                    return redirect('merchant_dashboard')
                else:
                    return redirect('home')
            else:
                # Failed login
                user.record_login_attempt(success=False, ip_address=ip_address, device_info=user_agent)
                log_security_event(user, 'LOGIN_FAILED', 'Invalid credentials', ip_address, user_agent)
                messages.error(request, 'Invalid username or password.')
                
        except User.DoesNotExist:
            # User not found - still log for security
            log_security_event(None, 'LOGIN_FAILED', f'Login attempt for non-existent user: {username}', ip_address, user_agent)
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'authentication/login.html')


@login_required
def logout_view(request):
    """Enhanced logout with session cleanup"""
    user = request.user
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    # End user session
    try:
        user_session = UserSession.objects.get(
            user=user,
            session_key=request.session.session_key,
            is_active=True
        )
        user_session.end_session()
    except UserSession.DoesNotExist:
        pass
    
    # Log security event
    log_security_event(user, 'LOGOUT', 'User logged out', ip_address, user_agent)
    
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')


def register_view(request):
    """Registration disabled. Accounts must be created by superuser."""
    messages.error(request, 'Self-registration is disabled. Contact TIMB admin to create an account.')
    return redirect('login')


@login_required
def profile_view(request):
    """Enhanced user profile management"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            # Update profile
            profile.company_name = request.POST.get('company_name', profile.company_name)
            profile.license_number = request.POST.get('license_number', profile.license_number)
            profile.business_address = request.POST.get('business_address', profile.business_address)
            profile.website = request.POST.get('website', profile.website)
            profile.bio = request.POST.get('bio', profile.bio)
            profile.theme_preference = request.POST.get('theme_preference', profile.theme_preference)
            
            # Handle file upload
            if 'profile_picture' in request.FILES:
                profile.profile_picture = request.FILES['profile_picture']
            
            # Update notification preferences
            profile.email_notifications = bool(request.POST.get('email_notifications'))
            profile.sms_notifications = bool(request.POST.get('sms_notifications'))
            
            profile.save()
            
            # Log security event
            ip_address = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            log_security_event(request.user, 'PROFILE_UPDATE', 'Profile updated', ip_address, user_agent)
            
            messages.success(request, 'Profile updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Profile update failed: {str(e)}')
    
    # Get user sessions
    active_sessions = UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-last_activity')
    
    context = {
        'profile': profile,
        'active_sessions': active_sessions,
    }
    
    return render(request, 'authentication/profile.html', context)


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """Change user password"""
    current_password = request.POST.get('current_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')
    
    if not request.user.check_password(current_password):
        messages.error(request, 'Current password is incorrect.')
        return redirect('profile')
    
    if new_password != confirm_password:
        messages.error(request, 'New passwords do not match.')
        return redirect('profile')
    
    if len(new_password) < 8:
        messages.error(request, 'New password must be at least 8 characters long.')
        return redirect('profile')
    
    # Update password
    request.user.set_password(new_password)
    request.user.password_changed_at = timezone.now()
    request.user.save()
    
    # End all other sessions
    UserSession.objects.filter(
        user=request.user,
        is_active=True
    ).exclude(session_key=request.session.session_key).update(
        is_active=False,
        logout_time=timezone.now()
    )
    
    # Log security event
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    log_security_event(request.user, 'PASSWORD_CHANGE', 'Password changed successfully', ip_address, user_agent)
    
    messages.success(request, 'Password changed successfully! Other sessions have been logged out.')
    return redirect('profile')


@login_required
@require_http_methods(["POST"])
def end_session(request):
    """End a specific user session"""
    session_id = request.POST.get('session_id')
    
    try:
        user_session = UserSession.objects.get(
            id=session_id,
            user=request.user,
            is_active=True
        )
        user_session.end_session()
        
        messages.success(request, 'Session ended successfully.')
        
    except UserSession.DoesNotExist:
        messages.error(request, 'Session not found.')
    
    return redirect('profile')


@login_required
@require_http_methods(["POST"])
def generate_secure_qr(request):
    """Generate secure QR code for data sharing"""
    try:
        data = json.loads(request.body)
        data_type = data.get('data_type')
        content = data.get('content')
        expiry_hours = int(data.get('expiry_hours', 24))
        max_uses = int(data.get('max_uses', 5))
        
        # Generate QR token
        qr_result = qr_manager.generate_access_token(
            {
                'type': data_type,
                'content': content,
                'generated_by': request.user.username,
                'timestamp': timezone.now().isoformat()
            },
            expiry_minutes=expiry_hours * 60
        )
        
        # Create token record
        qr_token = QRToken.objects.create(
            token=qr_result['token'],
            data_ref=qr_result['data_ref'],
            created_by=request.user,
            token_type=data_type,
            max_uses=max_uses,
            expires_at=timezone.now() + timezone.timedelta(hours=expiry_hours)
        )
        
        # Store encrypted data
        EncryptedData.objects.create(
            data_ref=qr_result['data_ref'],
            encrypted_content=qr_result['encrypted_data'],
            content_type=data_type,
            created_by=request.user,
            expires_at=qr_token.expires_at
        )
        
        # Log security event
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        log_security_event(
            request.user, 
            'TOKEN_GENERATED', 
            f'QR token generated for {data_type}', 
            ip_address, 
            user_agent
        )
        
        return JsonResponse({
            'success': True,
            'qr_code': qr_result['qr_code'],
            'token': qr_token.token,
            'expires_at': qr_token.expires_at.isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def verify_qr_token(request, token):
    """Verify and access QR token data"""
    try:
        qr_token = QRToken.objects.get(token=token)
        
        if not qr_token.is_valid():
            return JsonResponse({
                'success': False,
                'error': 'Token is invalid or expired'
            })
        
        # Get encrypted data
        try:
            encrypted_data = EncryptedData.objects.get(data_ref=qr_token.data_ref)
            
            if encrypted_data.is_expired():
                return JsonResponse({
                    'success': False,
                    'error': 'Data has expired'
                })
            
            # Use token
            if qr_token.use_token():
                content = encrypted_data.get_content()
                
                # Log access
                ip_address = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                log_security_event(
                    qr_token.created_by,
                    'TOKEN_USED',
                    f'QR token accessed: {token[:8]}...',
                    ip_address,
                    user_agent
                )
                
                return JsonResponse({
                    'success': True,
                    'data': content,
                    'uses_remaining': qr_token.max_uses - qr_token.access_count
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Token usage limit exceeded'
                })
                
        except EncryptedData.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Data not found'
            })
        
    except QRToken.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Invalid token'
        })


# Helper functions
def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_device_type(user_agent):
    """Determine device type from user agent"""
    user_agent = user_agent.lower()
    if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
        return 'mobile'
    elif 'tablet' in user_agent or 'ipad' in user_agent:
        return 'tablet'
    else:
        return 'desktop'


def get_browser_info(user_agent):
    """Extract browser information from user agent"""
    user_agent = user_agent.lower()
    if 'chrome' in user_agent:
        return 'Chrome'
    elif 'firefox' in user_agent:
        return 'Firefox'
    elif 'safari' in user_agent:
        return 'Safari'
    elif 'edge' in user_agent:
        return 'Edge'
    else:
        return 'Unknown'


def log_security_event(user, event_type, description, ip_address=None, user_agent='', severity='LOW', additional_data=None):
    """Log security event"""
    SecurityLog.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent,
        additional_data=additional_data or {}
    )


def send_verification_email(user, token):
    """Send email verification"""
    if hasattr(settings, 'EMAIL_HOST_USER') and settings.EMAIL_HOST_USER:
        try:
            verification_url = f"{settings.SITE_URL}/auth/verify/{token}/"
            
            subject = "Verify your TIMB account"
            message = f"""
            Hello {user.get_full_name() or user.username},
            
            Please click the link below to verify your email address:
            {verification_url}
            
            This link will expire in 24 hours.
            
            Best regards,
            TIMB Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send verification email: {e}")