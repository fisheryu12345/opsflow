<template>
  <div class="dfc">
    <el-form ref="formRef" :rules="rules" :model="f" label-width="100px" size="small">
      <el-form-item :label="$t('message.menuPage.deptParent')" prop="parent">
        <el-tree-select
          v-model="f.parent"
          :props="treeSelProps"
          :data="deptList"
          :cache-data="props.cacheData"
          lazy check-strictly
          :load="onTreeLoad"
          :placeholder="$t('message.menuPage.deptParentPlaceholder')"
          clearable
        />
      </el-form-item>
      <el-form-item :label="$t('message.menuPage.deptName')" prop="name">
        <el-input v-model="f.name" :placeholder="$t('message.menuPage.deptNamePlaceholder')" maxlength="50" />
      </el-form-item>
      <el-form-item :label="$t('message.menuPage.deptKey')" prop="key">
        <el-input v-model="f.key" :placeholder="$t('message.menuPage.deptKeyPlaceholder')" maxlength="50" />
      </el-form-item>
      <el-form-item :label="$t('message.menuPage.deptOwnerLabel')">
        <el-input v-model="f.owner" :placeholder="$t('message.menuPage.deptOwnerPlaceholder')" />
      </el-form-item>
      <el-form-item :label="$t('message.menuPage.deptDescLabel')">
        <el-input v-model="f.description" type="textarea" maxlength="200" show-word-limit :rows="3" :placeholder="$t('message.menuPage.deptDescPlaceholder')" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="loading" size="small" @click="onSubmit">
          {{ f.id ? $t('message.menuPage.deptSaveChanges') : $t('message.menuPage.deptNewDept') }}
        </el-button>
        <el-button size="small" @click="onCancel">{{ $t('message.menuPage.deptCancel') }}</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script lang="ts" setup>
import { reactive, ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElForm, FormRules } from 'element-plus';
import { lazyLoadDept, AddObj, UpdateObj } from '../../api';
import { successNotification } from '/@/utils/message';
import { DeptFormDataType, TreeItemType, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

const { t } = useI18n();

const props = withDefaults(defineProps<{ initFormData: TreeItemType | null; treeData: TreeItemType[]; cacheData: TreeItemType[] }>(), {
  initFormData: () => null, treeData: () => [], cacheData: () => [],
});
const emit = defineEmits(['drawerClose']);

const treeSelProps = { children: 'children', label: 'name', value: 'id', isLeaf: (_d: any, node: Node) => !node?.data?.hasChild };
const formRef = ref<InstanceType<typeof ElForm>>();
const rules: FormRules = { name: [{ required: true, message: t('message.menuPage.deptNameRequired'), trigger: 'blur' }], key: [{ required: true, message: t('message.menuPage.deptNameRequired'), trigger: 'blur' }] };

const deptList = ref<TreeItemType[]>([]);
const f = reactive<DeptFormDataType>({ key: '', parent: '', name: '', owner: '', description: '' });
const loading = ref(false);

const setData = () => {
  if (!props.initFormData?.id) return;
  f.id = props.initFormData.id;
  f.key = props.initFormData.key || '';
  f.parent = props.initFormData.parent || '';
  f.name = props.initFormData.name || '';
  f.owner = props.initFormData.owner || '';
  f.description = props.initFormData.description || '';
};

const onTreeLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) lazyLoadDept({ parent: node.data.id }).then((r: APIResponseData) => resolve(r.data));
};

const onSubmit = () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    loading.value = true;
    try {
      const res = f.id ? await UpdateObj(f) : await AddObj(f);
      if (res?.code === 2000) { successNotification(res.msg as string); emit('drawerClose', 'submit'); }
    } finally { loading.value = false; }
  });
};

const onCancel = () => emit('drawerClose');

onMounted(() => { props.treeData.forEach(i => deptList.value.push(i)); setData(); });
</script>

<style scoped lang="scss">
.dfc {
  padding: 20px; box-sizing: border-box;
}
</style>
