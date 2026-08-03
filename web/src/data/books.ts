export type BookStatus = 'unread' | 'reading' | 'paused' | 'done'

/** 与后端 Subject.SUBJECT_CHOICES 严格对齐 —— 阅读时上报给 /api/learning/study-sessions/accumulate/ 用 */
export type BookSubject =
  | 'data_structure'
  | 'cybersecurity'
  | 'iot'
  | 'electrical_automation'
  | 'mechanical_design'
  | 'advanced_math'
  | 'artificial_intelligence'

export interface BookConfig {
  id: string
  title: string
  author: string
  catName: string
  coverUrl: string
  pdfUrl: string
  chaptersTotal: number
  /** 所属学科 —— 读这本书时上报给后端, 归到对应学科的学习时长 */
  subject: BookSubject
}

// PDF 原始服务器前缀 → 腾讯云 COS 前缀（自动替换，填服务器地址即可）
const PDF_SERVER = 'http://62.234.70.182:5001/files/'
const COS_BASE = 'https://books-1305652127.cos.ap-beijing.myqcloud.com/'

function cosUrl(raw: string): string {
  return raw.startsWith(PDF_SERVER) ? COS_BASE + raw.slice(PDF_SERVER.length) : raw
}

// ═══════════════════════════════════════════════════════════════════════════
//  书架书单 ─ 直接将服务器返回的 JSON 粘贴替换下方数组即可更新书单
//
//  字段说明：
//    id            唯一标识，自定义，不可重复
//    title / author / catName / chaptersTotal  书目元数据，手动填写
//    pdfUrl        填服务器原始地址 (http://62.234.70.182:5001/files/xxx.pdf)
//                  程序自动将其转换为腾讯云 COS 地址
//    coverUrl      封面地址 (http://62.234.70.182:5001/api/files/<hash>/cover)
//
//  新增书籍：在数组末尾追加一条记录，重启前端即生效
//  页码：运行时由 PDF.js 自动解析，无需在此填写
// ═══════════════════════════════════════════════════════════════════════════
const RAW_BOOK_LIST: BookConfig[] = [
  {
    id: 'deep_learning_limu',
    title: '动手学深度学习',
    author: '李沐',
    catName: '计算机',
    chaptersTotal: 0,
    pdfUrl: 'http://62.234.70.182:5001/files/e4f7e1dafd8744d2a2d4b2747431fd71.pdf',
    coverUrl: 'https://books-1305652127.cos.ap-beijing.myqcloud.com/dongshouxue.png',
    subject: 'artificial_intelligence',
  },
  {
    id: 'data_structure_yan',
    title: '数据结构（C语言版 第2版）',
    author: '严蔚敏',
    catName: '计算机',
    chaptersTotal: 10,
    pdfUrl: 'http://62.234.70.182:5001/files/269c5de4eccd4f5784e3ec57dd276cf7.pdf',
    coverUrl: 'https://books-1305652127.cos.ap-beijing.myqcloud.com/shujujiegou.png',
    subject: 'data_structure',
  },
  {
    id: 'os_concepts_9th',
    title: '操作系统概念（原书第9版）',
    author: 'Silberschatz 等',
    catName: '计算机',
    chaptersTotal: 26,
    pdfUrl: 'http://62.234.70.182:5001/files/61d9ff0c5a3c455baa39aff470e4a774.pdf',
    coverUrl: 'https://books-1305652127.cos.ap-beijing.myqcloud.com/caozuoxitong.png',
    subject: 'data_structure',
  },
  {
    id: 'db_system_5th',
    title: '数据库系统概论（第5版）',
    author: '王珊 / 萨师煊',
    catName: '计算机',
    chaptersTotal: 15,
    pdfUrl: 'http://62.234.70.182:5001/files/104c504b5dde42c1a8da5f40fac6c956.pdf',
    coverUrl: 'https://books-1305652127.cos.ap-beijing.myqcloud.com/shujuku.png',
    subject: 'data_structure',
  },
  {
    id: 'computer_network_xie',
    title: '计算机网络',
    author: '谢希仁',
    catName: '计算机',
    chaptersTotal: 9,
    pdfUrl: 'http://62.234.70.182:5001/files/3736f97616e7401d82e6ccb7f6d115cc.pdf',
    coverUrl: 'https://books-1305652127.cos.ap-beijing.myqcloud.com/jisjiwangluo.png',
    subject: 'data_structure',
  },
]

// 自动将 pdfUrl 转换为 COS 地址后导出
export const BOOKS_CONFIG: readonly BookConfig[] = RAW_BOOK_LIST.map((b) => ({
  ...b,
  pdfUrl: cosUrl(b.pdfUrl),
}))
