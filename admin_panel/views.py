from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages as flash
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth import get_user_model

from mail.models import MessageMeta
from accounts.models import Mailbox, Domain, Alias
from accounts.services import dovecot_hash

@staff_member_required
def email_list(request):
    qs = MessageMeta.objects.select_related('mailbox').order_by('-date')
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/email_list.html', {'page': page})

@staff_member_required
def email_detail(request, pk):
    email = get_object_or_404(MessageMeta, pk=pk)
    if request.method == 'POST':
        folder = request.POST.get('folder')
        seen = request.POST.get('seen')
        if folder:
            email.folder = folder
        if seen is not None:
            email.seen = seen == 'true'
        email.save()
        flash.success(request, "Email metadata updated successfully.")
        return redirect(reverse('admin_panel:email_detail', args=[pk]))
    return render(request, 'admin_panel/email_detail.html', {'email': email})

@staff_member_required
def email_delete(request, pk):
    email = get_object_or_404(MessageMeta, pk=pk)
    email.delete()
    flash.success(request, "Email metadata deleted successfully.")
    return redirect('admin_panel:email_list')

# --- Mailbox Management ---
@staff_member_required
def mailbox_list(request):
    qs = Mailbox.objects.select_related('domain', 'user').order_by('-created_at')
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/mailbox_list.html', {'page': page})

@staff_member_required
def mailbox_create(request):
    if request.method == 'POST':
        address = request.POST.get('address', '').strip()
        password = request.POST.get('password', '').strip()
        quota_mb = int(request.POST.get('quota_mb', 2048))

        if '@' not in address:
            flash.error(request, "Invalid address. It must be in local_part@domain format.")
            return redirect('admin_panel:mailbox_list')

        local, domain_name = address.rsplit('@', 1)
        local = local.lower().strip()
        domain_name = domain_name.lower().strip()

        if not local or not domain_name:
            flash.error(request, "Username and Domain name cannot be empty.")
            return redirect('admin_panel:mailbox_list')

        try:
            domain, _ = Domain.objects.get_or_create(name=domain_name)
            User = get_user_model()
            user, created = User.objects.get_or_create(
                username=address, defaults={'email': address}
            )
            if created or password:
                user.set_password(password)
                user.save()

            if Mailbox.objects.filter(domain=domain, local_part=local).exists():
                flash.error(request, f"Mailbox {address} already exists.")
                return redirect('admin_panel:mailbox_list')

            Mailbox.objects.create(
                user=user,
                domain=domain,
                local_part=local,
                password_hash=dovecot_hash(password),
                quota_mb=quota_mb
            )
            flash.success(request, f"Mailbox {address} created successfully and is now live.")
        except Exception as e:
            flash.error(request, f"Error creating mailbox: {str(e)}")

    return redirect('admin_panel:mailbox_list')

@staff_member_required
def mailbox_delete(request, pk):
    mailbox = get_object_or_404(Mailbox, pk=pk)
    address = mailbox.address
    mailbox.delete()
    flash.success(request, f"Mailbox {address} deleted successfully.")
    return redirect('admin_panel:mailbox_list')

# --- Domain Management ---
@staff_member_required
def domain_list(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip().lower()
        dkim_selector = request.POST.get('dkim_selector', 'mail').strip()
        if name:
            if Domain.objects.filter(name=name).exists():
                flash.error(request, f"Domain {name} already exists.")
            else:
                Domain.objects.create(name=name, dkim_selector=dkim_selector)
                flash.success(request, f"Domain {name} added successfully.")
        return redirect('admin_panel:domain_list')

    qs = Domain.objects.order_by('-created_at')
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/domain_list.html', {'page': page})

@staff_member_required
def domain_delete(request, pk):
    domain = get_object_or_404(Domain, pk=pk)
    name = domain.name
    try:
        domain.delete()
        flash.success(request, f"Domain {name} deleted successfully.")
    except Exception as e:
        flash.error(request, f"Failed to delete domain (might have active mailboxes): {str(e)}")
    return redirect('admin_panel:domain_list')

# --- Alias Management ---
@staff_member_required
def alias_list(request):
    qs = Alias.objects.select_related('domain').order_by('domain__name', 'source')
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get('page'))
    domains = Domain.objects.filter(active=True)
    return render(request, 'admin_panel/alias_list.html', {'page': page, 'domains': domains})

@staff_member_required
def alias_create(request):
    if request.method == 'POST':
        domain_id = request.POST.get('domain')
        source = request.POST.get('source', '').strip().lower()
        destination = request.POST.get('destination', '').strip()

        domain = get_object_or_404(Domain, pk=domain_id)
        if not destination:
            flash.error(request, "Destination email is required.")
            return redirect('admin_panel:alias_list')

        try:
            Alias.objects.create(domain=domain, source=source, destination=destination)
            flash.success(request, f"Alias created successfully.")
        except Exception as e:
            flash.error(request, f"Failed to create alias: {str(e)}")

    return redirect('admin_panel:alias_list')

@staff_member_required
def alias_delete(request, pk):
    alias = get_object_or_404(Alias, pk=pk)
    alias.delete()
    flash.success(request, "Alias deleted successfully.")
    return redirect('admin_panel:alias_list')
