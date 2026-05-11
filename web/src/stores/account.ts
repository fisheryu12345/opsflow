import { defineStore } from 'pinia';
import { getAccountList } from '/@/api/stock/account';

interface AccountItem {
  id: number;
  name: string;
  initial_balance: string;
  current_equity: string;
  total_commission: string;
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
      try {
        const res: any = await getAccountList();
        if (res.code === 2000) {
          this.accounts = res.data || [];
          // 每个用户只能看到自己的账户（后端已过滤），默认选中第一个
          if (this.accounts.length > 0) {
            // 保留用户已有的选择（如果还在列表中），否则默认第一个
            const stillExists = this.currentAccountId && this.accounts.some(a => a.id === this.currentAccountId);
            if (!stillExists) {
              this.currentAccountId = this.accounts[0].id;
            }
          }
        }
      } catch (e) {
        console.error('获取账户列表失败:', e);
      } finally {
        this.loaded = true;
      }
    },
  },
});
