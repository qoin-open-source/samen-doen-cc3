from django.contrib import admin

from .models import Rule, RuleSet, Condition, RuleStatus, ActionStatus


class ConditionInline(admin.StackedInline):
    model = Condition


class RuleAdmin(admin.ModelAdmin):
    save_on_top = True
    list_display = ('name', 'description', 'ruleset', 'action_class',
                    'parameter_names', 'parameter_values', 'process_model',
                    'exit_on_match', 'exit_on_fail', 'perform_action_once',
                    'sequence', 'active')
    list_editable = ['active', ]
    inlines = [
        ConditionInline,
    ]
    

class RuleStatusAdmin(admin.ModelAdmin):
    list_display = ('rule', 'condition', 'content_type', 'object_id', 'identity')


class ActionStatusAdmin(admin.ModelAdmin):
    list_display = ('action', 'params', 'rule_status', 'performed')


admin.site.register(Rule, RuleAdmin)
admin.site.register(RuleSet)
admin.site.register(RuleStatus, RuleStatusAdmin)
admin.site.register(ActionStatus, ActionStatusAdmin)
