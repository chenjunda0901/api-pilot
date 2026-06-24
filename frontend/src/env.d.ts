/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue"
  const component: DefineComponent<object, object, unknown, object>
  export default component
}

declare module 'axios' {
  interface AxiosRequestConfig {
    _silent403?: boolean
  }
}
