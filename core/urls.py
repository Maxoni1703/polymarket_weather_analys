from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.root, name='root'),
    path('api/config', views.get_config, name='get_config'),
    path('api/market-prices', views.get_market_prices, name='get_market_prices'),
    path('api/analyze', views.analyze_city, name='analyze_city'),
    path('api/search', views.trigger_search, name='trigger_search'),
    path('api/settings', views.update_settings, name='update_settings'),
    path('api/chat', views.chat_with_ai, name='chat_with_ai'),
]
