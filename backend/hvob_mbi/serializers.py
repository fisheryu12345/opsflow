"""
HVOB-MBI serializers
"""
from rest_framework import serializers
from .models import HvobMbiWatchlistItem, HvobMbiDailyState


class HvobMbiWatchlistItemSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = HvobMbiWatchlistItem
        fields = '__all__'


class HvobMbiDailyStateSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.name', read_only=True)
    watchlist_count = serializers.SerializerMethodField()

    class Meta:
        model = HvobMbiDailyState
        exclude = ['created_at', 'updated_at']

    def get_watchlist_count(self, obj):
        return len(obj.watchlist) if obj.watchlist else 0
