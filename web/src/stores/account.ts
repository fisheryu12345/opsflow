import { defineStore } from 'pinia';
import { getAccountList } from '/@/api/stock/account';

interface AccountItem {
  id: number;
  name: string;
  initial_balance: string;
  current_equity: string;
  is_active: boolean;
}

export const useAccountStore = defineStore('account', {
  state: () => ({
    accounts: [] as AccountItem[],
    currentAccountId: null as number | null,
    loaded: false,
  }),
  getters: {},
  actions: {
    async fetchAccounts() {
      if (this.loaded) return
      try {
        const res: any = await getAccountList();
        if (res.code === 2000) {
          this.accounts = res.data || [];
          // 如果尚未选择账户，默认选中第一个
          if (this.accounts.length > 0 && !this.currentAccountId) {
            const saved = localStorage.getItem('currentAccountId');
            if (saved && this.accounts.some((a) => a.id === Number(saved))) {
              this.currentAccountId = Number(saved);
            } else {
              this.currentAccountId = this.accounts[0].id;
            }
          }
        }
      } catch (e) {
        console.error('获取账户列表失败:', e);
      } finally {
        // 无论成功失败都标记为已加载，避免重试死锁
        this.loaded = true;
      }
    },
  },
});
