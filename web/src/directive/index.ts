import type { App } from 'vue';
import vCan from '/@/directive/iamPermission';
import { wavesDirective, dragDirective } from '/@/directive/customDirective';

/**
 * Register global directives
 * v-can — IAM role-based permission (v-can.edit / v-can.admin)
 * v-waves — button ripple effect
 * v-drag — custom drag
 */
export function directive(app: App) {
  app.directive('can', vCan);
  wavesDirective(app);
  dragDirective(app);
}
