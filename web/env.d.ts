/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 后端 API 基础地址（不含协议），例如 127.0.0.1:8000 */
  readonly VITE_BASE_URL: string
  /** MiniMax API Key，用于书架阅读助手 */
  readonly VITE_MINIMAX_API_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
