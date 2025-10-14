from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    MerchantProfile,
    MerchantInventory,
    CustomGrade,
    GradeComponent,
    AggregationRule,
    ClientOrder,
    FarmerRiskAssessment,
    DashboardWidget,
    InterMerchantCommunication,
    InterMerchantTrade,
    PurchaseRecommendation,
    AggregationRuleSet,
    AggregatedGrade,
    AggregatedGradeComponent,
)


@admin.register(MerchantProfile)
class MerchantProfileAdmin(admin.ModelAdmin):
    list_display = (
        'merchant_name',
        'business_type',
        'profile_visibility',
        'show_contact_info',
        'allow_direct_contact',
        'created_at'
    )
    
    list_filter = (
        'business_type',
        'profile_visibility',
        'show_contact_info',
        'allow_direct_contact',
        'created_at'
    )
    
    search_fields = (
        'merchant__company_name',
        'business_description',
        'headquarters_address'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Merchant Information', {
            'fields': ('merchant',)
        }),
        ('Branding', {
            'fields': (
                'company_logo',
                'company_banner',
                'brand_colors'
            )
        }),
        ('Business Information', {
            'fields': (
                'business_type',
                'business_description',
                'founding_year',
                'number_of_employees',
                'annual_capacity'
            )
        }),
        ('Contact Information', {
            'fields': (
                'headquarters_address',
                'phone_primary',
                'phone_secondary',
                'email_business',
                'website_url'
            )
        }),
        ('Social Media', {
            'fields': (
                'linkedin_url',
                'facebook_url',
                'twitter_url'
            ),
            'classes': ('collapse',)
        }),
        ('Trading Preferences', {
            'fields': (
                'preferred_grades',
                'minimum_order_value',
                'payment_terms',
                'delivery_regions'
            ),
            'classes': ('collapse',)
        }),
        ('Visibility Settings', {
            'fields': (
                'profile_visibility',
                'show_contact_info',
                'show_business_stats',
                'show_certifications',
                'allow_direct_contact'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'


class GradeComponentInline(admin.TabularInline):
    model = GradeComponent
    extra = 1
    fields = ('base_grade', 'percentage', 'minimum_quantity')


@admin.register(CustomGrade)
class CustomGradeAdmin(admin.ModelAdmin):
    list_display = (
        'custom_grade_name',
        'merchant_name',
        'target_price',
        'quality_standard',
        'is_active',
        'is_draft',
        'created_at'
    )
    
    list_filter = (
        'quality_standard',
        'is_active',
        'is_draft',
        'created_at',
        'merchant'
    )
    
    search_fields = (
        'custom_grade_name',
        'merchant__company_name',
        'description'
    )
    
    inlines = [GradeComponentInline]
    
    readonly_fields = ('created_at', 'updated_at', 'base_cost', 'profit_margin')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'merchant',
                'custom_grade_name',
                'description'
            )
        }),
        ('Pricing', {
            'fields': (
                'target_price',
                'minimum_order_quantity',
                'base_cost',
                'profit_margin'
            )
        }),
        ('Quality Specifications', {
            'fields': (
                'quality_standard',
                'flavor_profile',
                'burn_rate',
                'moisture_content',
                'nicotine_level'
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_draft'
            )
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'


@admin.register(MerchantInventory)
class MerchantInventoryAdmin(admin.ModelAdmin):
    list_display = (
        'merchant_name',
        'grade_name',
        'quantity',
        'reserved_quantity',
        'available_quantity_display',
        'average_cost',
        'total_value_display',
        'last_updated'
    )
    
    list_filter = (
        'merchant',
        'grade__category',
        'last_purchase_date',
        'last_updated'
    )
    
    search_fields = (
        'merchant__company_name',
        'grade__grade_name',
        'storage_location'
    )
    
    readonly_fields = ('last_updated', 'total_value_display', 'available_quantity_display')
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'merchant',
                'grade',
                'quantity',
                'reserved_quantity',
                'available_quantity_display',
                'average_cost',
                'total_value_display'
            )
        }),
        ('Quality Information', {
            'fields': (
                'quality_grade',
                'moisture_content',
                'origin_location',
                'harvest_season'
            )
        }),
        ('Storage Information', {
            'fields': (
                'storage_location',
                'storage_conditions'
            )
        }),
        ('Dates', {
            'fields': (
                'last_purchase_date',
                'expiry_date',
                'last_updated'
            )
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'
    
    def grade_name(self, obj):
        return obj.grade.grade_name
    grade_name.short_description = 'Grade'
    grade_name.admin_order_field = 'grade__grade_name'
    
    def available_quantity_display(self, obj):
        return f"{obj.available_quantity} kg"
    available_quantity_display.short_description = 'Available'
    
    def total_value_display(self, obj):
        return f"${obj.total_value:,.2f}"
    total_value_display.short_description = 'Total Value'


@admin.register(ClientOrder)
class ClientOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'merchant_name',
        'client_name',
        'get_grade_name',
        'requested_quantity',
        'total_amount_display',
        'status',
        'payment_status',
        'created_at'
    )

    list_filter = (
        'status',
        'payment_status',
        'created_at',
        'merchant'
    )

    search_fields = (
        'order_number',
        'client_name',
        'client_email',
        'merchant__company_name'
    )

    readonly_fields = ('order_number', 'created_at', 'total_amount_display')

    fieldsets = (
        ('Order Information', {
            'fields': (
                'order_number',
                'merchant',
                'created_at'
            )
        }),
        ('Client Information', {
            'fields': (
                'client_name',
                'client_email',
                'client_phone',
                'client_address'
            )
        }),
        ('Order Details', {
            'fields': (
                'grade',
                'custom_grade',
                'requested_quantity',
                'target_price',
                'total_amount_display'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'payment_status',
                'expected_delivery_date',
                'actual_delivery_date'
            )
        }),
        ('Notes', {
            'fields': (
                'order_notes',
                'special_requirements'
            ),
            'classes': ('collapse',)
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'
    
    def total_amount_display(self, obj):
        return f"${obj.total_amount:,.2f}"
    total_amount_display.short_description = 'Total Amount'


@admin.register(FarmerRiskAssessment)
class FarmerRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'farmer_name',
        'merchant_name',
        'risk_level_display',
        'risk_score_display',
        'proposed_contract_value_display',
        'is_approved',
        'assessment_date'
    )
    
    list_filter = (
        'risk_level',
        'is_approved',
        'assessment_date',
        'merchant'
    )
    
    search_fields = (
        'farmer_name',
        'location',
        'merchant__company_name'
    )
    
    readonly_fields = (
        'assessment_date',
        'risk_score',
        'risk_level',
        'ai_recommendation',
        'risk_factors'
    )
    
    fieldsets = (
        ('Assessment Information', {
            'fields': (
                'merchant',
                'assessed_by',
                'assessment_date'
            )
        }),
        ('Farmer Information', {
            'fields': (
                'farmer_name',
                'farmer_id',
                'location',
                'phone'
            )
        }),
        ('Farm Details', {
            'fields': (
                'total_hectares',
                'years_experience',
                'primary_tobacco_type',
                'previous_yields'
            )
        }),
        ('Financial Information', {
            'fields': (
                'annual_income',
                'debt_level',
                'credit_score',
                'previous_defaults'
            )
        }),
        ('Contract Details', {
            'fields': (
                'proposed_contract_value',
                'proposed_quantity',
                'contract_duration_months'
            )
        }),
        ('AI Assessment Results', {
            'fields': (
                'risk_score',
                'risk_level',
                'ai_recommendation',
                'risk_factors'
            )
        }),
        ('Approval', {
            'fields': (
                'is_approved',
                'approval_notes'
            )
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'
    
    def risk_level_display(self, obj):
        colors = {
            'LOW': 'green',
            'MEDIUM': 'orange', 
            'HIGH': 'red',
            'CRITICAL': 'darkred'
        }
        color = colors.get(obj.risk_level, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_risk_level_display()
        )
    risk_level_display.short_description = 'Risk Level'
    
    def risk_score_display(self, obj):
        if obj.risk_score:
            percentage = float(obj.risk_score) * 100
            return f"{percentage:.1f}%"
        return "-"
    risk_score_display.short_description = 'Risk Score'
    
    def proposed_contract_value_display(self, obj):
        return f"${obj.proposed_contract_value:,.2f}"
    proposed_contract_value_display.short_description = 'Contract Value'


@admin.register(InterMerchantTrade)
class InterMerchantTradeAdmin(admin.ModelAdmin):
    list_display = (
        'trade_id',
        'seller_name',
        'buyer_name',
        'grade_name',
        'quantity',
        'total_value_display',
        'status_display',
        'is_flagged_for_review',
        'proposed_at'
    )
    
    list_filter = (
        'status',
        'is_flagged_for_review',
        'proposed_at',
        'grade__category'
    )
    
    search_fields = (
        'trade_id',
        'seller_merchant__company_name',
        'buyer_merchant__company_name',
        'grade__grade_name'
    )
    
    readonly_fields = (
        'trade_id',
        'proposed_at',
        'total_value_display',
        'fraud_risk_score'
    )
    
    fieldsets = (
        ('Trade Information', {
            'fields': (
                'trade_id',
                'seller_merchant',
                'buyer_merchant',
                'proposed_at'
            )
        }),
        ('Trade Details', {
            'fields': (
                'grade',
                'quantity',
                'agreed_price_per_kg',
                'total_value_display'
            )
        }),
        ('Status', {
            'fields': (
                'status',
                'agreed_at',
                'timb_reviewed_at',
                'completed_at'
            )
        }),
        ('TIMB Oversight', {
            'fields': (
                'timb_reviewer',
                'timb_notes',
                'is_flagged_for_review',
                'fraud_risk_score'
            )
        }),
        ('Documentation', {
            'fields': (
                'contract_document',
                'delivery_receipt'
            ),
            'classes': ('collapse',)
        })
    )
    
    def seller_name(self, obj):
        return obj.seller_merchant.company_name
    seller_name.short_description = 'Seller'
    seller_name.admin_order_field = 'seller_merchant__company_name'
    
    def buyer_name(self, obj):
        return obj.buyer_merchant.company_name
    buyer_name.short_description = 'Buyer'
    buyer_name.admin_order_field = 'buyer_merchant__company_name'
    
    def grade_name(self, obj):
        return obj.grade.grade_name
    grade_name.short_description = 'Grade'
    grade_name.admin_order_field = 'grade__grade_name'
    
    def total_value_display(self, obj):
        return f"${obj.total_value:,.2f}"
    total_value_display.short_description = 'Total Value'
    
    def status_display(self, obj):
        colors = {
            'PROPOSED': 'blue',
            'AGREED': 'green',
            'PENDING_TIMB_APPROVAL': 'orange',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'COMPLETED': 'darkgreen',
            'CANCELLED': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Status'


@admin.register(PurchaseRecommendation)
class PurchaseRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        'merchant_name',
        'recommendation_type_display',
        'grade_name',
        'recommended_quantity',
        'estimated_cost_display',
        'priority_display',
        'confidence_score_display',
        'is_active',
        'is_implemented',
        'generated_at'
    )
    
    list_filter = (
        'recommendation_type',
        'priority',
        'is_active',
        'is_implemented',
        'generated_at',
        'merchant'
    )
    
    search_fields = (
        'merchant__company_name',
        'grade__grade_name',
        'reasoning'
    )
    
    readonly_fields = (
        'confidence_score',
        'generated_at',
        'implemented_at',
        'expires_at',
        'is_expired'
    )
    
    fieldsets = (
        ('Recommendation Information', {
            'fields': (
                'merchant',
                'recommendation_type',
                'grade',
                'generated_at'
            )
        }),
        ('Recommendation Details', {
            'fields': (
                'recommended_quantity',
                'estimated_cost',
                'target_price',
                'expected_roi'
            )
        }),
        ('AI Analysis', {
            'fields': (
                'confidence_score',
                'priority',
                'reasoning',
                'market_factors'
            )
        }),
        ('Status', {
            'fields': (
                'is_active',
                'is_implemented',
                'implemented_at',
                'expires_at',
                'is_expired'
            )
        })
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    merchant_name.admin_order_field = 'merchant__company_name'
    
    def grade_name(self, obj):
        return obj.grade.grade_name
    grade_name.short_description = 'Grade'
    grade_name.admin_order_field = 'grade__grade_name'
    
    def recommendation_type_display(self, obj):
        return obj.get_recommendation_type_display()
    recommendation_type_display.short_description = 'Type'
    
    def estimated_cost_display(self, obj):
        return f"${obj.estimated_cost:,.2f}"
    estimated_cost_display.short_description = 'Estimated Cost'
    
    def priority_display(self, obj):
        colors = {
            'LOW': 'gray',
            'MEDIUM': 'blue',
            'HIGH': 'orange',
            'URGENT': 'red'
        }
        color = colors.get(obj.priority, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = 'Priority'
    
    def confidence_score_display(self, obj):
        percentage = float(obj.confidence_score) * 100
        return f"{percentage:.1f}%"
    confidence_score_display.short_description = 'Confidence'


@admin.register(AggregationRule)
class AggregationRuleAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'source_model',
        'source_field',
        'aggregation_type',
        'time_period',
        'is_active',
        'created_at'
    )

    list_filter = (
        'aggregation_type',
        'time_period',
        'is_active',
        'created_at'
    )

    search_fields = (
        'name',
        'source_model',
        'source_field'
    )


@admin.register(AggregationRuleSet)
class AggregationRuleSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'merchant', 'rule_type', 'is_active', 'created_at')
    list_filter = ('rule_type', 'is_active', 'created_at', 'merchant')
    search_fields = ('name', 'merchant__company_name')


@admin.register(AggregatedGrade)
class AggregatedGradeAdmin(admin.ModelAdmin):
    list_display = ('name', 'merchant', 'rule_set', 'total_quantity_kg', 'computed_at')
    list_filter = ('merchant', 'rule_set__rule_type', 'computed_at')
    search_fields = ('name', 'rule_set__name', 'merchant__company_name')


@admin.register(AggregatedGradeComponent)
class AggregatedGradeComponentAdmin(admin.ModelAdmin):
    list_display = ('aggregated_grade', 'base_grade', 'percentage', 'kilograms')
    list_filter = ('base_grade__category',)
    search_fields = ('aggregated_grade__name', 'base_grade__grade_code')

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'merchant_name',
        'widget_type',
        'position_display',
        'size_display',
        'is_visible'
    )
    
    list_filter = (
        'widget_type',
        'is_visible',
        'merchant'
    )
    
    search_fields = (
        'title',
        'merchant__company_name'
    )
    
    def merchant_name(self, obj):
        return obj.merchant.company_name
    merchant_name.short_description = 'Merchant'
    
    def position_display(self, obj):
        return f"({obj.position_x}, {obj.position_y})"
    position_display.short_description = 'Position'
    
    def size_display(self, obj):
        return f"{obj.width}x{obj.height}"
    size_display.short_description = 'Size'


@admin.register(InterMerchantCommunication)
class InterMerchantCommunicationAdmin(admin.ModelAdmin):
    list_display = (
        'subject',
        'from_merchant_name',
        'to_merchant_name',
        'message_type',
        'is_read',
        'is_flagged_by_ai',
        'sent_at'
    )
    
    list_filter = (
        'message_type',
        'is_read',
        'is_flagged_by_ai',
        'sent_at'
    )
    
    search_fields = (
        'subject',
        'message',
        'from_merchant__company_name',
        'to_merchant__company_name'
    )
    
    readonly_fields = ('sent_at', 'read_at')
    
    def from_merchant_name(self, obj):
        return obj.from_merchant.company_name
    from_merchant_name.short_description = 'From'
    
    def to_merchant_name(self, obj):
        return obj.to_merchant.company_name
    to_merchant_name.short_description = 'To'


# Customize admin site
admin.site.site_header = "TIMB Merchant Administration"
admin.site.site_title = "TIMB Merchant Admin"
admin.site.index_title = "Welcome to TIMB Merchant Administration"