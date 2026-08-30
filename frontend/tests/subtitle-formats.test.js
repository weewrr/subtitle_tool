import { describe, it, expect } from 'vitest'
import { Subtitle, Paragraph, TimeCode, SubtitleFormats } from '@/models/subtitle'

// ============================================================
// TimeCode
// ============================================================
describe('TimeCode 解析与格式化', () => {
  it('构造:毫秒到时分秒毫秒', () => {
    const t = new TimeCode(3661500) // 1h 1m 1.5s
    expect(t.hours).toBe(1)
    expect(t.minutes).toBe(1)
    expect(t.seconds).toBe(1)
    expect(t.milliseconds).toBe(500)
  })

  it('parse: SRT 逗号风格 HH:MM:SS,mmm', () => {
    const t = TimeCode.parse('01:02:03,456')
    expect(t.totalMilliseconds).toBe(1 * 3600000 + 2 * 60000 + 3 * 1000 + 456)
  })

  it('parse: VTT 点风格 HH:MM:SS.mmm', () => {
    const t = TimeCode.parse('00:02:03.050')
    expect(t.totalMilliseconds).toBe(2 * 60000 + 3 * 1000 + 50)
  })

  it('parse: MM:SS.mmm 短格式(仅两段分隔)', () => {
    const t = TimeCode.parse('05:30.100')
    expect(t.totalMilliseconds).toBe(5 * 60000 + 30 * 1000 + 100)
  })

  it('toSRTString / toVTTString 格式化匹配', () => {
    const t = new TimeCode(5 * 60000 + 3 * 1000 + 7)
    expect(t.toSRTString()).toBe('00:05:03,007')
    expect(t.toVTTString()).toBe('00:05:03.007')
  })

  it('setter 重写 hours/minutes/seconds 时其他字段保持', () => {
    const t = new TimeCode(0)
    t.hours = 1
    expect(t.totalMilliseconds).toBe(3600000)
    t.minutes = 10
    expect(t.totalMilliseconds).toBe(3600000 + 10 * 60000)
    t.seconds = 30
    expect(t.totalMilliseconds).toBe(3600000 + 10 * 60000 + 30 * 1000)
    t.milliseconds = 500
    expect(t.totalMilliseconds).toBe(3600000 + 600000 + 30000 + 500)
  })
})

// ============================================================
// Paragraph / Subtitle 基础操作 + 撤销栈
// ============================================================
describe('Subtitle 撤销/重做栈 (#7)', () => {
  function buildDemo() {
    const s = new Subtitle()
    s.paragraphs.push(new Paragraph(new TimeCode(0), new TimeCode(1000), 'A'))
    s.paragraphs.push(new Paragraph(new TimeCode(1000), new TimeCode(2000), 'B'))
    s.paragraphs.push(new Paragraph(new TimeCode(2000), new TimeCode(3000), 'C'))
    s.renumber()
    return s
  }

  it('初始 canUndo/canRedo 为 false', () => {
    const s = buildDemo()
    expect(s.canUndo).toBe(false)
    expect(s.canRedo).toBe(false)
  })

  it('saveHistory 入栈 → undo 回到之前', () => {
    const s = buildDemo()
    s.saveHistory('初始')
    expect(s.historyItems.length).toBe(1)
    expect(s.canUndo).toBe(true)
    // 修改第二行文本
    s.paragraphs[1].text = 'B-modified'
    s.undo()
    expect(s.paragraphs[1].text).toBe('B')
    expect(s.canUndo).toBe(false)
    expect(s.canRedo).toBe(true)
  })

  it('redo 还原修改,再新编辑清空 redo 栈', () => {
    const s = buildDemo()
    s.saveHistory('step1')
    s.paragraphs[0].text = 'A2'
    s.undo()
    expect(s.paragraphs[0].text).toBe('A')
    s.redo()
    expect(s.paragraphs[0].text).toBe('A2')
    expect(s.canRedo).toBe(false)

    // 新编辑清空 redo
    s.saveHistory('step2')
    s.paragraphs[1].text = 'B2'
    expect(s.redoItems.length).toBe(0)
  })

  it('超过 maxHistoryItems=100 时从队首丢弃', () => {
    const s = new Subtitle()
    s.paragraphs.push(new Paragraph(new TimeCode(0), new TimeCode(1000), 'X'))
    for (let i = 0; i < 110; i++) s.saveHistory(`step-${i}`)
    expect(s.historyItems.length).toBe(100)
    expect(s.historyItems[0].description).toBe('step-10') // 前 10 项被丢
  })
})

// ============================================================
// #7 历史栈序列化/反序列化(Subtitle.serializeHistory/restoreHistory)
// ============================================================
describe('Subtitle 历史栈持久化 (#7)', () => {
  it('serializeHistory → restoreHistory 往返后 undo 仍可用', () => {
    const s1 = new Subtitle()
    s1.paragraphs.push(new Paragraph(new TimeCode(0), new TimeCode(1000), 'p1'))
    s1.paragraphs.push(new Paragraph(new TimeCode(1000), new TimeCode(2000), 'p2'))
    s1.saveHistory('初始')
    s1.paragraphs[0].text = 'p1-modified'
    s1.saveHistory('改第一行')
    expect(s1.historyItems.length).toBe(2)

    const packed = s1.serializeHistory(30)
    expect(packed.undo).toHaveLength(2)
    expect(packed.undo[0].description).toBe('初始')

    // 新空 Subtitle 还原
    const s2 = new Subtitle()
    s2.restoreHistory(packed)
    expect(s2.historyItems.length).toBe(2)
    expect(s2.historyItems[1].description).toBe('改第一行')
    // 段落克隆成功(Paragraph 实例而非 plain object)
    expect(s2.historyItems[0].paragraphs[0].startTime).toBeInstanceOf(TimeCode)
    expect(s2.historyItems[0].paragraphs[0].text).toBe('p1')
  })

  it('maxItems 限制条数', () => {
    const s1 = new Subtitle()
    s1.paragraphs.push(new Paragraph(new TimeCode(0), new TimeCode(1000), 'x'))
    for (let i = 0; i < 10; i++) s1.saveHistory(`h${i}`)
    const packed = s1.serializeHistory(3)
    expect(packed.undo).toHaveLength(3)
    expect(packed.undo.map(h => h.description)).toEqual(['h7', 'h8', 'h9'])
  })

  it('restoreHistory 对空值/坏输入不抛错', () => {
    const s = new Subtitle()
    expect(() => s.restoreHistory(null)).not.toThrow()
    expect(() => s.restoreHistory({ undo: null, redo: undefined })).not.toThrow()
    expect(s.historyItems).toEqual([])
    expect(s.redoItems).toEqual([])
  })
})

// ============================================================
// SRT/VTT/TXT parse ↔ toXxx 往返
// ============================================================
describe('字幕格式 parse ↔ serialize 往返', () => {
  const srtSample = `1
00:00:01,000 --> 00:00:03,500
Hello world

2
00:00:04,000 --> 00:00:06,250
Second line`

  it('SRT parse → toSRT 内容等价', () => {
    const s = SubtitleFormats.parseSRT(srtSample)
    expect(s.paragraphs).toHaveLength(2)
    expect(s.paragraphs[0].text).toBe('Hello world')
    expect(s.paragraphs[0].startTime.totalMilliseconds).toBe(1000)
    expect(s.paragraphs[0].endTime.totalMilliseconds).toBe(3500)
    expect(s.paragraphs[1].number).toBe(2)
    const out = SubtitleFormats.toSRT(s)
    // 重新解析输出应与原段落一致
    const s2 = SubtitleFormats.parseSRT(out)
    expect(s2.paragraphs).toHaveLength(2)
    expect(s2.paragraphs[0].text).toBe('Hello world')
    expect(s2.paragraphs[0].startTime.totalMilliseconds).toBe(1000)
    expect(s2.paragraphs[1].endTime.totalMilliseconds).toBe(6250)
  })

  it('VTT 往返:保留 WEBVTT 头并正确解析', () => {
    const vtt = `WEBVTT

00:00:02.000 --> 00:00:04.000
First caption

00:00:05.500 --> 00:00:07.250
Second caption`
    const s = SubtitleFormats.parseVTT(vtt)
    expect(s.paragraphs).toHaveLength(2)
    expect(s.header).toBe('WEBVTT')
    expect(s.paragraphs[0].startTime.totalMilliseconds).toBe(2000)
    expect(s.paragraphs[1].endTime.totalMilliseconds).toBe(7250)
    const out = SubtitleFormats.toVTT(s)
    expect(out.startsWith('WEBVTT')).toBe(true)
    const s2 = SubtitleFormats.parseVTT(out)
    expect(s2.paragraphs.length).toBe(2)
    expect(s2.paragraphs[1].text).toBe('Second caption')
  })

  it('TXT 格式(时间 -- 时间 + 单行文本)解析', () => {
    const txt = `00:00:01.000 -- 00:00:03.000
One

00:00:04.000 -- 00:00:06.000
Two`
    const s = SubtitleFormats.parseTXT(txt)
    expect(s.paragraphs).toHaveLength(2)
    expect(s.paragraphs[0].text).toBe('One')
    expect(s.paragraphs[1].startTime.totalMilliseconds).toBe(4000)
    expect(s.paragraphs[1].endTime.totalMilliseconds).toBe(6000)
  })

  it('detectFormat 能正确识别 SRT / VTT / ASS / TXT / SMI', () => {
    expect(SubtitleFormats.detectFormat('WEBVTT\n...')).toBe('vtt')
    expect(SubtitleFormats.detectFormat(srtSample)).toBe('srt')
    expect(SubtitleFormats.detectFormat('[Script Info]\nTitle:X')).toBe('ass')
    expect(SubtitleFormats.detectFormat('<SYNC Start="100">Hi</SYNC>')).toBe('smi')
    expect(SubtitleFormats.detectFormat('00:00:01.000 -- 00:00:02.000\nX')).toBe('txt')
    expect(SubtitleFormats.detectFormat('完全乱码')).toBeNull()
  })
})

// ============================================================
// Paragraph 克隆 id 保留
// ============================================================
describe('Paragraph / TimeCode 边界', () => {
  it('Paragraph.clone() 保留所有字段 + id', () => {
    const p = new Paragraph(new TimeCode(100), new TimeCode(900), 'text')
    p.translation = '翻译'
    p.actor = 'Narrator'
    p.style = 'Default'
    p.isComment = true
    const c = p.clone()
    expect(c.id).toBe(p.id)
    expect(c.translation).toBe('翻译')
    expect(c.actor).toBe('Narrator')
    expect(c.style).toBe('Default')
    expect(c.isComment).toBe(true)
    expect(c.duration.totalMilliseconds).toBe(800)
    // 是深拷贝,互不影响
    c.text = 'changed'
    expect(p.text).toBe('text')
  })

  it('Paragraph.duration 支持 end==start(0ms) 及负值返回负(不抛错)', () => {
    const p1 = new Paragraph(new TimeCode(0), new TimeCode(0), '')
    expect(p1.duration.totalMilliseconds).toBe(0)
    const p2 = new Paragraph(new TimeCode(1000), new TimeCode(500), '')
    expect(p2.duration.totalMilliseconds).toBe(-500)
  })
})
