<template>
  <el-form ref="formRef" :rules="rules" :model="deptFormData" label-width="100px" class="dfc-form">
    <el-form-item label="父级部门" prop="parent">
      <el-tree-select
        v-model="deptFormData.parent"
        :props="defaultTreeProps"
        :data="deptDefaultList"
        :cache-data="props.cacheData"
        lazy
        check-strictly
        :load="handleTreeLoad"
        placeholder="请选择父级部门"
        style="width:100%"
      />
    </el-form-item>
    <el-form-item label="部门名称" prop="name">
      <el-input v-model="deptFormData.name" placeholder="请输入部门名称" maxlength="50" />
    </el-form-item>
    <el-form-item label="部门标识" prop="key">
      <el-input v-model="deptFormData.key" placeholder="请输入唯一标识" maxlength="50" />
    </el-form-item>
    <el-form-item label="负责人">
      <el-input v-model="deptFormData.owner" placeholder="请输入负责人" />
    </el-form-item>
    <el-form-item label="备注">
      <el-input v-model="deptFormData.description" type="textarea" maxlength="200" show-word-limit :rows="3" placeholder="可选" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" :loading="deptBtnLoading" round @click="handleUpdateMenu">
        {{ deptFormData.id ? '保存修改' : '新增部门' }}
      </el-button>
      <el-button @click="handleClose">取消</el-button>
    </el-form-item>
  </el-form>
</template>

<script lang="ts" setup>
import { reactive, ref, onMounted } from 'vue';
import { ElForm, FormRules } from 'element-plus';
import { lazyLoadDept, AddObj, UpdateObj } from '../../api';
import { successNotification } from '/@/utils/message';
import { DeptFormDataType, TreeItemType, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

interface IProps { initFormData: TreeItemType | null; treeData: TreeItemType[]; cacheData: TreeItemType[]; }

const defaultTreeProps = {
  children: 'children', label: 'name', value: 'id',
  isLeaf: (data: TreeItemType, node: Node) => !node?.data.hasChild,
};

const formRef = ref<InstanceType<typeof ElForm>>();
const rules = reactive<FormRules>({
  name: [{ required: true, message: '部门名称必填', trigger: 'blur' }],
  key: [{ required: true, message: '部门标识必填', trigger: 'blur' }],
});

const props = withDefaults(defineProps<IProps>(), { initFormData: () => null, treeData: () => [], cacheData: () => [] });
const emit = defineEmits(['drawerClose']);

const deptDefaultList = ref<TreeItemType[]>([]);
const deptFormData = reactive<DeptFormDataType>({ key: '', parent: '', name: '', owner: '', description: '' });
const deptBtnLoading = ref(false);

const setFormData = () => {
  if (props.initFormData?.id) {
    deptFormData.id = props.initFormData.id;
    deptFormData.key = props.initFormData.key || '';
    deptFormData.parent = props.initFormData.parent || '';
    deptFormData.name = props.initFormData.name || '';
    deptFormData.owner = props.initFormData.owner || '';
    deptFormData.description = props.initFormData.description || '';
  }
};

const handleTreeLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) lazyLoadDept({ parent: node.data.id }).then((res: APIResponseData) => resolve(res.data));
};

const handleUpdateMenu = () => {
  formRef.value?.validate(async (valid) => {
    if (!valid) return;
    deptBtnLoading.value = true;
    try {
      const res = deptFormData.id ? await UpdateObj(deptFormData) : await AddObj(deptFormData);
      if (res?.code === 2000) { successNotification(res.msg as string); handleClose('submit'); }
    } finally { deptBtnLoading.value = false; }
  });
};

const handleClose = (type = '') => { emit('drawerClose', type); formRef.value?.resetFields(); };

onMounted(() => { props.treeData.forEach(i => deptDefaultList.value.push(i)); setFormData(); });
</script>

<style scoped lang="scss">
.dfc-form {
  padding: 20px;
  box-sizing: border-box;
}
</style>
