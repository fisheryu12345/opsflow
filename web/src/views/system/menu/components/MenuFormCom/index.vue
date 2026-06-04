<template>
  <div class="menu-form-com">
    <!-- Form tips / 表单提示 -->
    <div class="mf-alert">
      <el-icon size="14" style="flex-shrink:0"><InfoFilled /></el-icon>
      <div class="mf-alert-text">
        1. Red asterisk means required / 红色星号表示必填;<br />
        2. For catalog menus, component path may be empty / 添加菜单，如果是目录，组件地址为空即可;<br />
        3. For root menus, parent can be empty / 添加根节点菜单，父级菜单为空即可.
      </div>
    </div>

    <el-form ref="formRef" :rules="rules" :model="menuFormData" label-width="90px" label-position="top" size="default" class="mf-form">
      <!-- Row 1: Name + Parent -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="Menu Name / 菜单名称" prop="name">
            <el-input v-model="menuFormData.name" placeholder="Enter menu name / 请输入菜单名称" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Parent Menu / 父级菜单" prop="parent">
            <el-tree-select
              v-model="menuFormData.parent"
              :props="defaultTreeProps"
              :data="deptDefaultList"
              :cache-data="props.cacheData"
              lazy
              check-strictly
              clearable
              :load="handleTreeLoad"
              placeholder="Select parent / 请选择父级菜单"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- Row 2: Route + Icon -->
      <el-row :gutter="16">
        <el-col :span="12">
          <el-form-item label="Route Path / 路由地址" prop="web_path">
            <el-input v-model="menuFormData.web_path" placeholder="Start with / / 请以/开头" />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="Icon / 图标" prop="icon">
            <IconSelector clearable v-model="menuFormData.icon" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- Row 3: Switches Row 1 -->
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="Status / 状态">
            <el-switch v-model="menuFormData.status" width="60" inline-prompt active-text="Enable / 启用" inactive-text="Disable / 禁用" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item v-if="menuFormData.status" label="Sidebar / 侧边显示">
            <el-switch v-model="menuFormData.visible" width="60" inline-prompt active-text="Show / 显示" inactive-text="Hide / 隐藏" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="Cache / 缓存">
            <el-switch v-model="menuFormData.cache" width="60" inline-prompt active-text="Enable / 启用" inactive-text="Disable / 禁用" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- Row 4: Switches Row 2 -->
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item label="Is Catalog / 是否目录">
            <el-switch v-model="menuFormData.is_catalog" width="60" inline-prompt active-text="Yes / 是" inactive-text="No / 否" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item v-if="!menuFormData.is_catalog" label="External Link / 外链接">
            <el-switch v-model="menuFormData.is_link" width="60" inline-prompt active-text="Yes / 是" inactive-text="No / 否" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item v-if="!menuFormData.is_catalog" label="Is Affix / 是否固定">
            <el-switch v-model="menuFormData.is_affix" width="60" inline-prompt active-text="Yes / 是" inactive-text="No / 否" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- Row 5: Iframe -->
      <el-row :gutter="16">
        <el-col :span="8">
          <el-form-item v-if="!menuFormData.is_catalog && menuFormData.is_link" label="Is Iframe / 是否内嵌">
            <el-switch v-model="menuFormData.is_iframe" width="60" inline-prompt active-text="Yes / 是" inactive-text="No / 否" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- Divider -->
      <el-divider class="mf-divider" />

      <!-- Row 6: Component section -->
      <div v-if="!menuFormData.is_catalog">
        <el-row :gutter="16">
          <el-col :span="12" v-if="!menuFormData.is_link">
            <el-form-item label="Component Path / 组件地址" prop="component">
              <el-autocomplete
                class="w-full"
                v-model="menuFormData.component"
                :fetch-suggestions="querySearch"
                :trigger-on-focus="false"
                clearable
                :debounce="100"
                placeholder="Enter component path / 输入组件地址"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="!menuFormData.is_link">
            <el-form-item label="Component Name / 组件名称" prop="component_name">
              <el-input v-model="menuFormData.component_name" placeholder="Enter component name / 请输入组件名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="menuFormData.is_link">
            <el-form-item label="Link URL / 外链接" prop="link_url">
              <el-input v-model="menuFormData.link_url" placeholder="Enter link URL / 请输入外链接地址" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Description -->
      <el-form-item label="Description / 备注">
        <el-input v-model="menuFormData.description" maxlength="200" show-word-limit type="textarea" :rows="3" placeholder="Enter description / 请输入备注" />
      </el-form-item>

      <el-divider class="mf-divider" />

      <!-- Submit / Cancel Buttons -->
      <div class="mf-actions">
        <el-button @click="handleSubmit" type="primary" :loading="menuBtnLoading" class="mf-btn-primary">
          <el-icon><Check /></el-icon> Save / 保存
        </el-button>
        <el-button @click="handleCancel" class="mf-btn-cancel">
          Cancel / 取消
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, reactive } from 'vue';
import { ElForm, FormRules } from 'element-plus';
import { InfoFilled, Check } from '@element-plus/icons-vue';
import IconSelector from '/@/components/iconSelector/index.vue';
import { lazyLoadMenu, AddObj, UpdateObj } from '../../api';
import { successNotification } from '/@/utils/message';
import { MenuFormDataType, MenuTreeItemType, ComponentFileItem, APIResponseData } from '../../types';
import type Node from 'element-plus/es/components/tree/src/model/node';

interface IProps {
  initFormData: Partial<MenuTreeItemType> | null;
  treeData: MenuTreeItemType[];
  cacheData: MenuTreeItemType[];
}

const defaultTreeProps: any = {
  children: 'children',
  label: 'name',
  value: 'id',
  isLeaf: (data: MenuTreeItemType[], node: Node) => {
    if (node?.data.hasChild) {
      return false;
    } else {
      return true;
    }
  },
};

const validateWebPath = (rule: any, value: string, callback: Function) => {
  const pattern = /^\/.*?/;
  if (pattern.test(value)) {
    callback();
  } else {
    callback(new Error('Please enter a valid path / 请输入正确的地址'));
  }
};

const validateLinkUrl = (rule: any, value: string, callback: Function) => {
  const pattern = /^\/.*?/;
  const patternUrl = /http(s)?:\/\/([\w-]+\.)+[\w-]+(\/[\w- .\/?%&=]*)?/;
  if (pattern.test(value) || patternUrl.test(value)) {
    callback();
  } else {
    callback(new Error('Please enter a valid URL / 请输入正确的地址'));
  }
};

const props = withDefaults(defineProps<IProps>(), {
  initFormData: () => null,
  treeData: () => [],
  cacheData: () => [],
});
const emit = defineEmits(['drawerClose']);

const formRef = ref<InstanceType<typeof ElForm>>();

const rules = reactive<FormRules>({
  web_path: [{ required: true, message: 'Please enter a valid path / 请输入正确的地址', validator: validateWebPath, trigger: 'blur' }],
  name: [{ required: true, message: 'Menu name is required / 菜单名称必填', trigger: 'blur' }],
  component: [{ required: true, message: 'Component path is required / 请输入组件地址', trigger: 'blur' }],
  component_name: [{ required: true, message: 'Component name is required / 请输入组件名称', trigger: 'blur' }],
  link_url: [{ required: true, message: 'Link URL is required / 请输入外链接地址', validator: validateLinkUrl, trigger: 'blur' }],
});

let deptDefaultList = ref<MenuTreeItemType[]>([]);
let menuFormData = reactive<MenuFormDataType>({
  parent: '',
  name: '',
  component: '',
  web_path: '',
  icon: '',
  cache: true,
  status: true,
  visible: true,
  component_name: '',
  description: '',
  is_catalog: false,
  is_link: false,
  is_iframe: false,
  is_affix: false,
  link_url: '',
});
let menuBtnLoading = ref(false);

const setMenuFormData = () => {
  if (props.initFormData?.id) {
    menuFormData.id = props.initFormData?.id || '';
    menuFormData.name = props.initFormData?.name || '';
    menuFormData.parent = props.initFormData?.parent || '';
    menuFormData.component = props.initFormData?.component || '';
    menuFormData.web_path = props.initFormData?.web_path || '';
    menuFormData.icon = props.initFormData?.icon || '';
    menuFormData.status = !!props.initFormData.status;
    menuFormData.visible = !!props.initFormData.visible;
    menuFormData.cache = !!props.initFormData.cache;
    menuFormData.component_name = props.initFormData?.component_name || '';
    menuFormData.description = props.initFormData?.description || '';
    menuFormData.is_catalog = !!props.initFormData.is_catalog;
    menuFormData.is_link = !!props.initFormData.is_link;
    menuFormData.is_iframe = !!props.initFormData.is_iframe;
    menuFormData.is_affix = !!props.initFormData.is_affix;
    menuFormData.link_url = props.initFormData.link_url || '';
  }
};

const querySearch = (queryString: string, cb: any) => {
  const files: any = import.meta.glob('@views/**/*.vue');
  let fileLists: Array<any> = [];
  Object.keys(files).forEach((qs: string) => {
    fileLists.push({
      label: qs.replace(/(\.\/|\.vue)/g, ''),
      value: qs.replace(/(\.\/|\.vue)/g, ''),
    });
  });
  const results = queryString ? fileLists.filter(createFilter(queryString)) : fileLists;
  results.forEach((val) => {
    val.label = val.label.replace('/src/views/', '');
    val.value = val.value.replace('/src/views/', '');
  });
  cb(results);
};

const createFilter = (queryString: string) => {
  return (file: ComponentFileItem) => {
    return file.value.toLowerCase().indexOf(queryString.toLowerCase()) !== -1;
  };
};

/**
 * Lazy load tree / 树的懒加载
 */
const handleTreeLoad = (node: Node, resolve: Function) => {
  if (node.level !== 0) {
    lazyLoadMenu({ parent: node.data.id }).then((res: APIResponseData) => {
      resolve(res.data);
    });
  }
};

const handleSubmit = () => {
  if (!formRef.value) return;
  formRef.value.validate(async (valid) => {
    if (!valid) return;
    try {
      let res;
      menuBtnLoading.value = true;
      if (menuFormData.id) {
        res = await UpdateObj(menuFormData);
      } else {
        res = await AddObj(menuFormData);
      }
      if (res?.code === 2000) {
        successNotification(res.msg as string);
        handleCancel('submit');
      }
    } finally {
      menuBtnLoading.value = false;
    }
  });
};

const handleCancel = (type: string = '') => {
  emit('drawerClose', type);
  formRef.value?.resetFields();
};

onMounted(async () => {
  props.treeData.map((item) => {
    deptDefaultList.value.push(item);
  });
  setMenuFormData();
});
</script>

<style lang="scss" scoped>
@import '../../../apps/opsflow/styles/opsflow-global';

.menu-form-com {
  padding: 4px 0;
}

/* ===== Alert ===== */
.mf-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 20px;
  border-radius: $of-radius-sm;
  background: $of-gradient-hero;
  border-left: 3px solid $of-color-primary;
  font-size: 12px;
  line-height: 1.7;
  color: $of-text-secondary;
}

.mf-alert-text {
  flex: 1;
  min-width: 0;
}

/* ===== Form ===== */
.mf-form {
  :deep(.el-form-item) {
    margin-bottom: 18px;
  }

  :deep(.el-form-item__label) {
    font-size: 13px;
    font-weight: 500;
    color: $of-text-primary;
    padding-bottom: 4px;
  }

  :deep(.el-input__wrapper),
  :deep(.el-autocomplete .el-input__wrapper) {
    border-radius: 6px;
    transition: box-shadow $of-transition-default, border-color $of-transition-default;
  }

  :deep(.el-input__wrapper:hover),
  :deep(.el-autocomplete .el-input__wrapper:hover) {
    box-shadow: 0 0 0 1px $of-color-primary inset;
  }

  :deep(.el-switch) {
    --el-switch-on-color: #409eff;
  }
}

/* ===== Divider ===== */
.mf-divider {
  margin: 12px 0 18px;
  border-top-color: $of-border-light;
}

/* ===== Actions ===== */
.mf-actions {
  display: flex;
  gap: 10px;
  padding-top: 8px;
}

.mf-btn-primary {
  min-width: 120px;
  transition: transform $of-transition-default, box-shadow $of-transition-default;

  &:hover {
    transform: translateY(-1px);
    box-shadow: $of-shadow-primary;
  }
}

.mf-btn-cancel {
  transition: transform $of-transition-default;

  &:hover {
    transform: translateY(-1px);
  }
}
</style>
