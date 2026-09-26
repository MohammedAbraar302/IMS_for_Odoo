from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    # Auth
    path('signup/', views.signup_view, name='signup'),
    path('signup/verify/', views.signup_verify_view, name='signup_verify'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.otp_reset_view, name='reset_password'),
    
    # Core Dashboard & Profile
    path('', views.dashboard_view, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    
    # Products & Categories
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:pk>/update/', views.product_update, name='product_update'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/', views.category_list, name='category_list'),
    
    # Receipts (Incoming Stock)
    path('receipts/', views.receipt_list, name='receipt_list'),
    path('receipts/create/', views.receipt_create, name='receipt_create'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('receipts/items/<int:pk>/delete/', views.receipt_item_delete, name='receipt_item_delete'),
    path('receipts/<int:pk>/validate/', views.receipt_validate, name='receipt_validate'),
    
    # Deliveries (Outgoing Stock)
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/create/', views.delivery_create, name='delivery_create'),
    path('deliveries/<int:pk>/', views.delivery_detail, name='delivery_detail'),
    path('deliveries/items/<int:pk>/delete/', views.delivery_item_delete, name='delivery_item_delete'),
    path('deliveries/<int:pk>/validate/', views.delivery_validate, name='delivery_validate'),
    
    # Internal Transfers
    path('transfers/', views.transfer_list, name='transfer_list'),
    path('transfers/create/', views.transfer_create, name='transfer_create'),
    path('transfers/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfers/<int:pk>/validate/', views.transfer_validate, name='transfer_validate'),
    
    # Adjustments
    path('adjustments/', views.adjustment_list, name='adjustment_list'),
    path('adjustments/create/', views.adjustment_create, name='adjustment_create'),
    path('adjustments/<int:pk>/', views.adjustment_detail, name='adjustment_detail'),
    
    # Move History (Stock Ledger)
    path('move-history/', views.move_history_view, name='move_history'),
    
    # Settings (Warehouse & Locations)
    path('settings/', views.warehouse_settings, name='settings'),
]
