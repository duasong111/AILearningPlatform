// markdown-it-texmath 没有 @types 包, 简单 shim 一下让 TS 闭嘴.
//   它的实际 export 是 markdown-it PluginWithOptions 形状的函数.
declare module 'markdown-it-texmath' {
  import type { PluginWithOptions } from 'markdown-it'
  const texmath: PluginWithOptions<unknown>
  export default texmath
}
