<template>
  <div class="menu-form-com">
    <!-- Form tips / 表单提示 -->
    <div class="mf-alert">
      <el-icon size="14" style="flex-shrink:0"><InfoFilled /></el-icon>
      <div class="mf-alert-text" v-html="$t('message.menuPage.formTips')" />
    </div>

    <el-form ref="formRef" :rules="rules" :model="menuFormData" label-position="top" size="default" class="mf-form">

      <!-- Section: Basic Info -->
      <div class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.menuName') }} / Name (EN)</div>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item :label="$t('message.menuPage.menuName')" prop="name">
              <el-input v-model="menuFormData.name" :placeholder="$t('message.menuPage.menuNamePlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('message.menuPage.nameEn')" prop="name_en">
              <el-input v-model="menuFormData.name_en" :placeholder="$t('message.menuPage.nameEnPlaceholder')" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Section: Route & Icon -->
      <div class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.routePath') }} / {{ $t('message.menuPage.icon') }}</div>
        <el-row :gutter="14">
          <el-col :span="12">
            <el-form-item :label="$t('message.menuPage.routePath')" prop="web_path">
              <el-input v-model="menuFormData.web_path" :placeholder="$t('message.menuPage.routePathPlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('message.menuPage.icon')" prop="icon">
              <IconSelector clearable v-model="menuFormData.icon" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Section: Parent -->
      <div class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.parentMenu') }}</div>
        <el-form-item prop="parent">
          <el-tree-select
            v-model="menuFormData.parent"
            :props="defaultTreeProps"
            :data="deptDefaultList"
            :cache-data="props.cacheData"
            lazy check-strictly clearable
            :load="handleTreeLoad"
            :placeholder="$t('message.menuPage.parentMenuPlaceholder')"
            style="width: 100%"
          />
        </el-form-item>
      </div>

      <!-- Section: Switches -->
      <div class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.status') }} / {{ $t('message.menuPage.cache') }}</div>
        <el-row :gutter="14">
          <el-col :span="8">
            <el-form-item :label="$t('message.menuPage.status')">
              <el-switch v-model="menuFormData.status" width="60" inline-prompt
                :active-text="$t('message.menuPage.statusEnable')"
                :inactive-text="$t('message.menuPage.statusDisable')" />
            </el-form-item>
          </el-col>
          <el-col :span="8" v-if="menuFormData.status">
            <el-form-item :label="$t('message.menuPage.sidebar')">
              <el-switch v-model="menuFormData.visible" width="60" inline-prompt
                :active-text="$t('message.menuPage.sidebarShow')"
                :inactive-text="$t('message.menuPage.sidebarHide')" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item :label="$t('message.menuPage.cache')">
              <el-switch v-model="menuFormData.cache" width="60" inline-prompt
                :active-text="$t('message.menuPage.cacheEnable')"
                :inactive-text="$t('message.menuPage.cacheDisable')" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="14" style="margin-top:6px">
          <el-col :span="6">
            <el-form-item :label="$t('message.menuPage.isCatalog')">
              <el-switch v-model="menuFormData.is_catalog" width="60" inline-prompt
                :active-text="$t('message.menuPage.catalogYes')"
                :inactive-text="$t('message.menuPage.catalogNo')" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="!menuFormData.is_catalog">
            <el-form-item :label="$t('message.menuPage.externalLink')">
              <el-switch v-model="menuFormData.is_link" width="60" inline-prompt
                :active-text="$t('message.menuPage.linkYes')"
                :inactive-text="$t('message.menuPage.linkNo')" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="!menuFormData.is_catalog">
            <el-form-item :label="$t('message.menuPage.isAffix')">
              <el-switch v-model="menuFormData.is_affix" width="60" inline-prompt
                :active-text="$t('message.menuPage.affixYes')"
                :inactive-text="$t('message.menuPage.affixNo')" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="!menuFormData.is_catalog && menuFormData.is_link">
            <el-form-item :label="$t('message.menuPage.isIframe')">
              <el-switch v-model="menuFormData.is_iframe" width="60" inline-prompt
                :active-text="$t('message.menuPage.iframeYes')"
                :inactive-text="$t('message.menuPage.iframeNo')" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Section: Component -->
      <div v-if="!menuFormData.is_catalog" class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.componentPath') }} / {{ $t('message.menuPage.componentName') }}</div>
        <el-row :gutter="14">
          <el-col :span="12" v-if="!menuFormData.is_link">
            <el-form-item :label="$t('message.menuPage.componentPath')" prop="component">
              <el-autocomplete
                class="w-full"
                v-model="menuFormData.component"
                :fetch-suggestions="querySearch"
                :trigger-on-focus="false" clearable :debounce="100"
                :placeholder="$t('message.menuPage.componentPathPlaceholder')"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="!menuFormData.is_link">
            <el-form-item :label="$t('message.menuPage.componentName')" prop="component_name">
              <el-input v-model="menuFormData.component_name" :placeholder="$t('message.menuPage.componentNamePlaceholder')" />
            </el-form-item>
          </el-col>
          <el-col :span="12" v-if="menuFormData.is_link">
            <el-form-item :label="$t('message.menuPage.linkUrl')" prop="link_url">
              <el-input v-model="menuFormData.link_url" :placeholder="$t('message.menuPage.linkUrlPlaceholder')" />
            </el-form-item>
          </el-col>
        </el-row>
      </div>

      <!-- Description -->
      <div class="mf-section">
        <div class="mf-sec-title">{{ $t('message.menuPage.description') }}</div>
        <el-form-item>
          <el-input v-model="menuFormData.description" maxlength="200" show-word-limit type="textarea" :rows="3"
            :placeholder="$t('message.menuPage.descriptionPlaceholder')" />
        </el-form-item>
      </div>

      <!-- Submit / Cancel -->
      <div class="mf-actions">
        <el-button @click="handleCancel" class="mf-btn-cancel">
          {{ $t('message.menuPage.cancel') }}
        </el-button>
        <el-button @click="handleSubmit" type="primary" :loading="menuBtnLoading" class="mf-btn-primary">
          <el-icon><Check /></el-icon> {{ $t('message.menuPage.save') }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted, reactive } from 'vue';
import { ElForm, FormRules } from 'element-plus';
import { InfoFilled, Check, Link } from '@element-plus/icons-vue';
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
  label: 'name_display',
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
    callback(new Error(t('message.menuPage.routePathRequired')));
  }
};

const validateLinkUrl = (rule: any, value: string, callback: Function) => {
  const pattern = /^\/.*?/;
  const patternUrl = /http(s)?:\/\/([\w-]+\.)+[\w-]+(\/[\w- .\/?%&=]*)?/;
  if (pattern.test(value) || patternUrl.test(value)) {
    callback();
  } else {
    callback(new Error(t('message.menuPage.routePathRequired')));
  }
};

import { useI18n } from 'vue-i18n';
const { t } = useI18n();

const props = withDefaults(defineProps<IProps>(), {
  initFormData: () => null,
  treeData: () => [],
  cacheData: () => [],
});
const emit = defineEmits(['drawerClose']);

const formRef = ref<InstanceType<typeof ElForm>>();

const rules = reactive<FormRules>({
  web_path: [{ required: true, message: t('message.menuPage.routePathRequired'), validator: validateWebPath, trigger: 'blur' }],
  name: [{ required: true, message: t('message.menuPage.menuNameRequired'), trigger: 'blur' }],
  component: [{ required: true, message: t('message.menuPage.componentPathRequired'), trigger: 'blur' }],
  component_name: [{ required: true, message: t('message.menuPage.componentNameRequired'), trigger: 'blur' }],
  link_url: [{ required: true, message: t('message.menuPage.linkUrlRequired'), validator: validateLinkUrl, trigger: 'blur' }],
});

let deptDefaultList = ref<MenuTreeItemType[]>([]);
let menuFormData = reactive<MenuFormDataType>({
  parent: '',
  name: '',
  name_en: '',
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
    menuFormData.name_en = props.initFormData?.name_en || '';
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
@use '../../../../../styles/opsflow-global' as *;

.menu-form-com {
  padding: 4px 0;
}

/* ===== Alert ===== */
.mf-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  margin-bottom: 20px;
  border-radius: $of-radius-sm;
  background: linear-gradient(135deg, #f0f4ff 0%, #f8f9fb 100%);
  border-left: 3px solid $of-color-primary;
  font-size: 12px;
  line-height: 1.8;
  color: $of-text-muted;
}

.mf-alert-text { flex: 1; min-width: 0; }

/* ===== Section ===== */
.mf-section {
  background: $of-bg-card;
  border: 1px solid $of-border-card;
  border-radius: $of-radius-sm;
  padding: 14px 16px;
  margin-bottom: 14px;
}

.mf-sec-title {
  font-size: 13px;
  font-weight: 600;
  color: $of-text-primary;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid $of-border-light;
}

/* ===== Form ===== */
.mf-form {
  :deep(.el-form-item) {
    margin-bottom: 0;
  }
  :deep(.el-form-item__label) {
    font-size: 12px;
    font-weight: 500;
    color: $of-text-secondary;
    padding-bottom: 2px;
  }
  :deep(.el-input__wrapper),
  :deep(.el-autocomplete .el-input__wrapper) {
    border-radius: 6px;
  }
  :deep(.el-switch) {
    --el-switch-on-color: #409eff;
  }
}

/* ===== Actions ===== */
.mf-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid $of-border-light;
}

.mf-btn-primary {
  min-width: 110px;
  transition: transform $of-transition-default, box-shadow $of-transition-default;
  &:hover {
    transform: translateY(-1px);
    box-shadow: $of-shadow-primary;
  }
}

.mf-btn-cancel {
  transition: transform $of-transition-default;
  &:hover { transform: translateY(-1px); }
}
</style>
