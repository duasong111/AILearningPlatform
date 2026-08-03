// Re-export 桥, 让 view 用更准确的名字 import.
//   旧文件 use_profile_chat_ws.ts 已升级为通用 useConvWS, 路径保留兼容.
export { useConvWS, type WSStatus } from './use_profile_chat_ws'
