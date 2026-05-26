from django.db import models
from decimal import Decimal


class HvobMbiConfig(models.Model):
    """HVOB-MBI 策略参数配置（每账户）"""
    account = models.OneToOneField(
        'stock.TradingAccount', on_delete=models.CASCADE,
        related_name='hvob_config', verbose_name='交易账户'
    )
    is_active = models.BooleanField('启用', default=True)
    risk_percent = models.DecimalField('单笔风险比例', max_digits=5, decimal_places=4, default=Decimal('0.005'))
    max_daily_loss_percent = models.DecimalField('单日最大亏损比例', max_digits=5, decimal_places=4, default=Decimal('0.02'))
    fix_reward_risk_ratio = models.DecimalField('固定盈亏比', max_digits=4, decimal_places=2, default=Decimal('1.5'))
    trailing_stop_enabled = models.BooleanField('启用移动止盈', default=True)
    trailing_stop_trigger_times = models.DecimalField('移动止盈触发倍数', max_digits=4, decimal_places=1, default=Decimal('2.0'))
    min_watchlist_size = models.IntegerField('观察池最小数量', default=5)
    max_positions_per_day = models.IntegerField('单日最大持仓数', default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'HVOB-MBI 策略配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"HVOB-{self.account.name}"


class HvobMbiDailyState(models.Model):
    """HVOB-MBI 每日状态快照"""
    account = models.ForeignKey('stock.TradingAccount', on_delete=models.CASCADE, related_name='hvob_daily_states')
    trade_date = models.DateField(db_index=True)
    watchlist = models.JSONField('观察池', default=list)
    mbi_value = models.DecimalField('MBI 值', max_digits=8, decimal_places=4, null=True, blank=True)
    mbi_label = models.CharField('MBI 标签', max_length=20, blank=True)
    opening_ranges = models.JSONField('开盘区间 {symbol: {H,L,R}}', default=dict)
    night_opening_ranges = models.JSONField('夜盘开盘区间 {symbol: {H,L,R,closed}}', default=dict)
    banned_symbols = models.JSONField('拉黑品种', default=list)
    traded_symbols = models.JSONField('已交易品种', default=list)
    total_trades = models.IntegerField('总交易次数', default=0)
    daily_pnl = models.DecimalField('日盈亏', max_digits=15, decimal_places=2, default=Decimal('0'))
    daily_loss = models.DecimalField('日累计亏损', max_digits=15, decimal_places=2, default=Decimal('0'))
    is_complete = models.BooleanField('是否完成', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'HVOB-MBI 日状态'
        verbose_name_plural = verbose_name
        unique_together = ('account', 'trade_date')

    def __str__(self):
        return f"HVOB-{self.account.name}-{self.trade_date}"


class HvobMbiWatchlistItem(models.Model):
    """HVOB-MBI 每日观察池条目"""
    account = models.ForeignKey('stock.TradingAccount', on_delete=models.CASCADE, verbose_name='交易账户')
    trade_date = models.DateField('交易日期', db_index=True)
    rank = models.IntegerField('排名')
    symbol = models.CharField('合约代码', max_length=50)
    product_code = models.CharField('品种代码', max_length=20)
    score = models.FloatField('综合评分', default=0)
    atr_pct = models.FloatField('ATR%', default=0)
    avg_amp = models.FloatField('5日平均振幅', default=0)
    vol_ratio = models.FloatField('量比', default=0)
    atr_score = models.FloatField('ATR得分', default=0)
    amp_score = models.FloatField('振幅得分', default=0)
    vol_score = models.FloatField('量能得分', default=0)
    bonus = models.IntegerField('品种奖惩', default=0)
    open_interest = models.IntegerField('持仓量', default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'HVOB 观察池条目'
        verbose_name_plural = verbose_name
        ordering = ['-trade_date', 'rank']
        unique_together = ('account', 'trade_date', 'symbol')

    def __str__(self):
        return f"{self.trade_date} #{self.rank} {self.symbol} ({self.score:.2f})"
