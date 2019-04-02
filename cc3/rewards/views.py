import logging
import os
from _mysql import OperationalError

from django.conf import settings
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import ObjectDoesNotExist, Q
from django.http import Http404, HttpResponse, HttpResponseRedirect, \
    HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView, View, UpdateView

from formtools.wizard.views import SessionWizardView

#  from cc3.core.models import Transaction
from cc3.cyclos.models import CyclosGroup, User
from cc3.cyclos.utils import (get_cyclos_connection,
                              close_cyclos_connection,
                              get_cyclos_transfer_totals)

from .models import UserCause
from .forms import (BulkRewardUploadFileForm, BulkRewardUploadDetailsForm,
                    BulkRewardUploadConfirmationForm,
                    UserCausePercentageForm
    )
from .utils import process_csv
from cc3.rewards.models import DefaultGoodCause

LOG = logging.getLogger(__name__)


class CauseListView(ListView):
    """
    Generic ``ListView`` class to be used in all 'causes' related views.
    """
    model = User
    context_object_name = 'causes'
    paginate_by = 9

    def get_context_data(self, **kwargs):
        """
        Overrides base ``get_context_data`` method to show the amounts of the
        contributions to the current good cause and to all good causes.
        """
        context = super(CauseListView, self).get_context_data(**kwargs)

        donation_type_id = getattr(settings,
                                   'GOOD_CAUSE_DONATION_TRANSFER_TYPE_ID', 32)

        # Calculate donations to all causes, for this user and
        # total for all users
        cause_usernames = [cause.username for cause in self.object_list]
        LOG.debug("cause_usernames: {0}".format(cause_usernames))
        if self.object_list.count():
            recipients = cause_usernames
        else:
            recipients = None   # get_cyclos_transfer_totals checks for None

        this_user_username = self.request.user.username

        try:
            conn = get_cyclos_connection()

            all_user_totals = get_cyclos_transfer_totals(
                conn,
                group_by='recipient',
                recipients=recipients,
                transfer_type_ids=(donation_type_id,))
            LOG.debug("all_user_totals: {0}".format(all_user_totals))

            # repeat the query, this time for just the current user
            my_totals = get_cyclos_transfer_totals(
                conn,
                group_by='recipient',
                senders=(this_user_username,),
                recipients=recipients,
                transfer_type_ids=(donation_type_id,))
            LOG.debug("my_totals: {0}".format(my_totals))

            context['total_donations'] = my_totals.get('_TOTAL_', 0)
            context['total_donations_all_users'] = all_user_totals.get(
                '_TOTAL_', 0)
        except OperationalError:
            context['total_donations'] = None
            context['total_donations_all_users'] = None

        try:
            current_cause = self.request.user.usercause.cause.username
        except ObjectDoesNotExist:
            current_cause = None
            context['cause_donations'] = None
            context['cause_donations_all_users'] = None
        if current_cause:
            if current_cause in cause_usernames:
                context['cause_donations'] = my_totals.get(current_cause, 0)
                context['cause_donations_all_users'] = all_user_totals.get(
                    current_cause, 0)
            else:
                # need to make another query
                current_cause_totals = get_cyclos_transfer_totals(
                    conn,
                    group_by='sender',
                    recipients=(current_cause,),
                    transfer_type_ids=(donation_type_id,))
                LOG.debug("current_cause_totals: {0}".format(
                    current_cause_totals))
                context['cause_donations'] = current_cause_totals.get(
                    this_user_username, 0)
                context['cause_donations_all_users'] = current_cause_totals.get(
                    '_TOTAL_', 0)

        #

        context['donations_reference'] = my_totals
        context['donations_reference_all_users'] = all_user_totals

        close_cyclos_connection(conn)

        return context

    def get_queryset(self):
        """
        Overrides base ``get_queryset`` method to provide a list of profiles
        related to 'Good causes' Cyclos group.
        """
        user_profile = self.request.user.cc3_profile

        try:
            cyclos_group = CyclosGroup.objects.get(
                name=settings.CYCLOS_CHARITY_MEMBER_GROUP)
            # excluding the currently selected cause from the list of causes
            return User.objects.filter(
                cc3_profile__cyclos_group=cyclos_group,
                cc3_profile__community=user_profile.community
            ).exclude(pk=user_profile.user.usercause.cause.pk).order_by(
                '-is_active',  # put inactive (good cause) users to back
                'cc3_profile__user'  # existing ordering
            )
        except CyclosGroup.DoesNotExist:
            LOG.critical('Charity causes Cyclos group does not exist.')
        except AttributeError:
            LOG.critical("Django setting CYCLOS_CHARITY_MEMBER_GROUP not"
                         " defined.")

        # Missing project settings. Cannot properly retrieve charity profiles.
        return User.objects.none()


class SelectCauseListView(CauseListView):
    template_name = 'rewards/select_cause.html'

    def get_context_data(self, **kwargs):
        """
        Add the current cause / donation_percentage
        """
        context = super(SelectCauseListView, self).get_context_data(**kwargs)

        try:
            user_cause = UserCause.objects.get(consumer=self.request.user)
            context['form'] = UserCausePercentageForm(
                instance=user_cause,
                community=self.request.user.cc3_profile.community,
                )
            context['default_cause'] = DefaultGoodCause.objects.get(community=self.request.user.cc3_profile.community)
            context['user_cause'] = user_cause
            context['donation_percent'] = user_cause.donation_percent
        except UserCause.DoesNotExist:
            context['form'] = UserCausePercentageForm(community=self.request.user.cc3_profile.community,)
        except DefaultGoodCause.DoesNotExist:
            context['default_cause'] = None
        return context

class UpdateDonationPercentageView(SuccessMessageMixin, UpdateView):
    template_name = 'rewards/update_donation_percentage_form.html'
    success_url = reverse_lazy('causes_list')
    context_object_name = 'user_cause'

    form_class = UserCausePercentageForm

    def get_object(self):
        user_cause = get_object_or_404(UserCause, consumer=self.request.user)
        self.old_donation_percent = user_cause.donation_percent
        return user_cause

    def get_form_kwargs(self):
        kwargs = super(UpdateDonationPercentageView, self).get_form_kwargs()
        kwargs['community'] = self.request.user.cc3_profile.community
        return kwargs

    def get_success_message(self, cleaned_data):
        if self.old_donation_percent is None:
            msg = _('Donation percentage set to {0}%').format(
            self.object.donation_percent)
        else:
            msg = _('Donation percentage updated from {1}% to {0}%').format(
            self.object.donation_percent, self.old_donation_percent)
        return msg

class SearchCauseListView(CauseListView):
    template_name = 'rewards/search_cause.html'

    def dispatch(self, request, *args, **kwargs):
        """
        Override ``dispatch`` base method to check if any query string was
        submitted. If not, bounce back to the main causes view.
        """
        if not self.request.GET.get('query'):
            return HttpResponseRedirect(reverse('causes_list'))

        return super(SearchCauseListView, self).dispatch(
            request, *args, **kwargs)

    def get_queryset(self):
        """
        Override ``get_queryset`` base method to retrieve only causes based on
        the string queried by the user.
        """
        queryset = super(SearchCauseListView, self).get_queryset()

        query_string = self.request.GET.get('query')

        query = (
            Q(username__icontains=query_string) |
            Q(first_name__icontains=query_string) |
            Q(last_name__icontains=query_string) |
            Q(email__icontains=query_string) |
            Q(cc3_profile__business_name__icontains=query_string) |
            Q(cc3_profile__slug__icontains=query_string)
        )

        return queryset.filter(query)

    def get_context_data(self, **kwargs):
        context = super(SearchCauseListView, self).get_context_data(**kwargs)
        context['query'] = self.request.GET.get('query')

        return context


class JoinCauseView(View):
    pattern_name = 'causes_list'

    def get(self, request, *args, **kwargs):
        cause = get_object_or_404(
            User, pk=int(kwargs.get('cause_pk')))

        good_cause_group = getattr(settings, 'CYCLOS_CHARITY_MEMBER_GROUP', '')
        if not good_cause_group:
            LOG.critical(u'Django setting CYCLOS_CHARITY_MEMBER_GROUP not'
                         u' defined.')
            raise Http404

        if cause.cc3_profile.cyclos_group.name == good_cause_group:
            try:
                user_cause = UserCause.objects.get(consumer=request.user)
            except UserCause.DoesNotExist:
                user_cause = UserCause(consumer=request.user)

            user_cause.cause = cause
            user_cause.save()

            LOG.info(u'User {0} joined good cause {1}'.format(
                self.request.user, cause))

            return HttpResponseRedirect(reverse('causes_list'))

        raise Http404


class BulkRewardUploadWizard(SessionWizardView):
    #template_name = 'rewards/bulk_upload_form.html'
    file_storage = FileSystemStorage(
        location=os.path.join(settings.MEDIA_ROOT, 'temp_uploads'))  # TODO

    def get_context_data(self, form, **kwargs):
        context = super(BulkRewardUploadWizard, self).get_context_data(
            form=form, **kwargs)
        if self.steps.current == '2':
            # re-validate the file, this time recording counts to
            # display on the form
            data = self.get_all_cleaned_data()
            summary = process_csv(data, make_payments=False)
            context.update(summary)
        return context

    def get_template_names(self):
        return ['rewards/bulk_upload_form_{0}.html'.format(
            self.steps.current)]

    def get_form_kwargs(self, step):
        kwargs = {}
        if step in ['1', '2']:
            # If at second or third step, pass in the file info and request.user
            # for initialising the dropdowns etc.
            data = self.get_cleaned_data_for_step('0')
            kwargs.update({
                'has_headers': data.get('has_headers', False),
                'csv_file': data.get('csv_file'),
                'community': self.request.user.cc3_profile.community,
                'can_vary_percent':
                    self.request.user.cc3_profile.cyclos_group.is_institution_group,
                })
        if step == '2':
            # add the column mapping info
            data = self.get_cleaned_data_for_step('1')
            kwargs.update(data)

        return kwargs

    def done(self, form_list, **kwargs):

        csv_file = form_list[0].cleaned_data['csv_file']
        LOG.info("Rewards bulk upload: Uploaded file {0}".format(csv_file.name))

        # Re-read the file and actually make the payments
        data = self.get_all_cleaned_data()
        summary = process_csv(
            data, make_payments=True, sender=self.request.user)
        amount_paid = summary.get('amount_paid', 0)

        # no need to keep the file
        self.file_storage.delete(csv_file.name)

        messages.add_message(
            self.request, messages.INFO, _(
                'Rewards applied successfully. Total amount paid: {0}'
                ).format(amount_paid))

        # redirect to account home (which will show message)
        return HttpResponseRedirect(reverse('accounts_home'))


# Create view function from BulkRewardUploadWizard with forms provided.
bulk_reward_upload_wizard = BulkRewardUploadWizard.as_view([
    BulkRewardUploadFileForm, BulkRewardUploadDetailsForm,
    BulkRewardUploadConfirmationForm])


##########################
# Admin related data views
##########################

@login_required
def admin_causes_list(request):
    """
    Creates a list of tabulated data for some javascript in the default
    good causes section
    This javascript updates the causes based on the community selected
    """
    if not request.user.is_superuser:
        return HttpResponseForbidden('Only available to admin users')

    causes = None
    try:
        cyclos_group = CyclosGroup.objects.get(
            name=settings.CYCLOS_CHARITY_MEMBER_GROUP)
        causes = User.objects.filter(
            cc3_profile__cyclos_group=cyclos_group)
    except CyclosGroup.DoesNotExist:
        LOG.critical('Charity causes Cyclos group does not exist.')
    except AttributeError:
        LOG.critical("Django setting CYCLOS_CHARITY_MEMBER_GROUP not"
                     " defined.")

    data = []
    for x in causes:
        try:
            data.append([
                u"%s" % x.cc3_profile.community.id,
                u"%s" % x.id,
                u"%s" % x.business_name
            ])
        except Exception, e:
            LOG.critical(
                u"Could not add {0} ({1}) to default good cause "
                u"admin {2}".format(
                    x.business_name, x.id, e.message))

    data = [u'\t'.join(line) for line in data]
    return HttpResponse(u'\n'.join(data), content_type='text/plain')
