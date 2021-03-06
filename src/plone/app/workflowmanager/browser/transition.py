from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from Products.DCWorkflow.Transitions import TRIGGER_AUTOMATIC
from Products.DCWorkflow.Transitions import TRIGGER_USER_ACTION

from plone.app.workflowmanager.browser.controlpanel import Base
from plone.app.workflowmanager.utils import clone_transition
from plone.app.workflowmanager.browser import validators
from plone.app.workflowmanager.permissions import allowed_guard_permissions

from plone.app.workflowmanager import WMMessageFactory as _


class AddTransition(Base):
    template = ViewPageTemplateFile('templates/add-new-transition.pt')

    def __call__(self):
        self.errors = {}

        if not self.request.get('form.actions.add', False):
            return self.handle_response(tmpl=self.template)
        else:
            self.authorize()
            transition = validators.not_empty(self, 'transition-name')
            transition_id = validators.id(self, 'transition-name',
                self.selected_workflow)

            if not self.errors:
                # must have transition to go on
                workflow = self.selected_workflow

                workflow.transitions.addTransition(transition_id)
                new_transition = workflow.transitions[transition_id]
                clone_of_id = self.request.get('clone-from-transition')
                new_transition.title = transition

                if clone_of_id:
                    # manage_copy|paste|clone doesn't work?
                    clone_transition(new_transition,
                        workflow.transitions[clone_of_id])
                else:
                    new_transition.actbox_name = transition
                    new_transition.actbox_url = \
    "%(content_url)s/content_status_modify?workflow_action=" + transition_id
                    new_transition.actbox_category = 'workflow'

                # if added from state screen
                referenced_state = self.request.get('referenced-state', None)
                if referenced_state:
                    state = self.selected_workflow.states[referenced_state]
                    state.transitions += (new_transition.id, )

                return self.handle_response(
                    message=_('msg_transition_created',
                        default=u'"${transition_id}" transition successfully created.',
                        mapping={'transition_id': new_transition.id}),
                    slideto=True,
                    transition=new_transition)
            else:
                return self.handle_response(tmpl=self.template,
                                            justdoerrors=True)


class SaveTransition(Base):

    def update_guards(self):
        wf = self.selected_workflow
        transition = self.selected_transition
        guard = transition.getGuard()

        perms = []
        for key, perm in allowed_guard_permissions.items():
            key = 'transition-%s-guard-permission-%s' % (transition.id, key)
            if key in self.request and perm not in guard.permissions:
                perms.append(perm)
        guard.permissions = tuple(perms)

        roles = validators.parse_set_value(self, 'transition-%s-guard-roles' %
            transition.id)
        okay_roles = set(wf.getAvailableRoles())
        guard.roles = tuple(roles & okay_roles)

        groups = validators.parse_set_value(self,
            'transition-%s-guard-groups' %
                transition.id)
        okay_groups = set([g['id'] for g in self.getGroups()])
        guard.groups = tuple(groups & okay_groups)

        transition.guard = guard

    def update_transition_properties(self):
        transition = self.selected_transition

        if ('transition-%s-autotrigger' % transition.id) in self.request:
            transition.trigger_type = TRIGGER_AUTOMATIC
        else:
            transition.trigger_type = TRIGGER_USER_ACTION

        if ('transition-%s-display-name' % transition.id) in self.request:
            transition.actbox_name = \
                self.request.get('transition-%s-display-name' % transition.id)

        if ('transition-%s-new-state' % transition.id) in self.request:
            transition.new_state_id = \
                self.request.get('transition-%s-new-state' % transition.id)

        if ('transition-%s-title' % transition.id) in self.request:
            transition.title = \
                self.request.get('transition-%s-title' % transition.id)

        if ('transition-%s-description' % transition.id) in self.request:
            transition.description = \
                self.request.get('transition-%s-description' % transition.id)

        for state in self.available_states:
            key = 'transition-%s-state-%s-selected' % (transition.id, state.id)
            if key in self.request:
                if transition.id not in state.transitions:
                    state.transitions += (transition.id, )
            else:
                if transition.id in state.transitions:
                    transitions = list(state.transitions)
                    transitions.remove(transition.id)
                    state.transitions = transitions

    def __call__(self):
        self.authorize()
        self.errors = {}

        self.update_guards()
        self.update_transition_properties()

        return self.handle_response()


class DeleteTransition(Base):
    template = ViewPageTemplateFile('templates/delete-transition.pt')

    def __call__(self):
        self.errors = {}
        transition = self.selected_transition
        id = transition.id

        if self.request.get('form.actions.delete', False) == 'Delete':
            self.authorize()
            #delete any associated rules also.
            self.actions.delete_rule_for(self.selected_transition)

            self.selected_workflow.transitions.deleteTransitions([id])
            # now check if we have any dangling references
            for state in self.available_states:
                if id in state.transitions:
                    transitions = list(state.transitions)
                    transitions.remove(id)
                    state.transitions = tuple(transitions)

            msg = _('msg_transition_deleted',
                    default=u'"${id}" transition has been successfully deleted.',
                    mapping={'id': id})
            return self.handle_response(message=msg)
        elif self.request.get('form.actions.cancel', False) == 'Cancel':
            msg = _('msg_deleting_canceled',
                    default=u'Deleting the "${id}" transition has been canceled.',
                    mapping={'id': id})
            return self.handle_response(message=msg)
        else:
            return self.handle_response(tmpl=self.template)
