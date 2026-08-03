/**
 * 课程封面配置
 * 使用 recraft 生成的插画封面（本地资源，避免远程链接过期），整体风格统一为蓝白科技风。
 *
 * 注意: 学科 code 与显示名并不完全一致，但封面按 code 映射。
 *   electrical_automation → 显示 "Python 编程"
 *   mechanical_design     → 显示 "操作系统"
 *   advanced_math         → 显示 "软件工程"
 */
import dataStructureCover from '@/assets/covers/data_structure_gen.png'
import cybersecurityCover from '@/assets/covers/cybersecurity_gen.png'
import iotCover from '@/assets/covers/iot_gen.png'
import artificialIntelligenceCover from '@/assets/covers/artificial_intelligence_gen.png'
import pythonCover from '@/assets/covers/python_gen.png'
import osCover from '@/assets/covers/os_gen.png'
import seCover from '@/assets/covers/se_gen.png'

export const SUBJECT_COVERS: Record<string, string> = {
  data_structure: dataStructureCover,
  cybersecurity: cybersecurityCover,
  iot: iotCover,
  electrical_automation: pythonCover, // Python 编程
  mechanical_design: osCover, // 操作系统
  advanced_math: seCover, // 软件工程
  artificial_intelligence: artificialIntelligenceCover,
}
