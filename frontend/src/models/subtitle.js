export class TimeCode {
  constructor(totalMilliseconds = 0) {
    this.totalMilliseconds = totalMilliseconds
  }

  get hours() {
    return Math.floor(this.totalMilliseconds / 3600000) % 24
  }

  set hours(value) {
    this.totalMilliseconds = (this.totalMilliseconds % 3600000) + value * 3600000
  }

  get minutes() {
    return Math.floor(this.totalMilliseconds / 60000) % 60
  }

  set minutes(value) {
    const ms = this.milliseconds
    const h = this.hours
    this.totalMilliseconds = h * 3600000 + value * 60000 + ms
  }

  get seconds() {
    return Math.floor(this.totalMilliseconds / 1000) % 60
  }

  set seconds(value) {
    const ms = this.milliseconds
    const h = this.hours
    const m = this.minutes
    this.totalMilliseconds = h * 3600000 + m * 60000 + value * 1000 + ms
  }

  get milliseconds() {
    return Math.floor(this.totalMilliseconds % 1000)
  }

  set milliseconds(value) {
    const h = this.hours
    const m = this.minutes
    const s = this.seconds
    this.totalMilliseconds = h * 3600000 + m * 60000 + s * 1000 + value
  }

  static parse(timeString) {
    const parts = timeString.split(/[:.,]/)
    if (parts.length === 4) {
      const hours = parseInt(parts[0], 10)
      const minutes = parseInt(parts[1], 10)
      const seconds = parseInt(parts[2], 10)
      const ms = parseInt(parts[3].padEnd(3, '0'), 10)
      return new TimeCode(hours * 3600000 + minutes * 60000 + seconds * 1000 + ms)
    } else if (parts.length === 3) {
      const minutes = parseInt(parts[0], 10)
      const seconds = parseInt(parts[1], 10)
      const ms = parseInt(parts[2].padEnd(3, '0'), 10)
      return new TimeCode(minutes * 60000 + seconds * 1000 + ms)
    }
    return new TimeCode(0)
  }

  toSRTString() {
    return `${String(this.hours).padStart(2, '0')}:${String(this.minutes).padStart(2, '0')}:${String(this.seconds).padStart(2, '0')},${String(this.milliseconds).padStart(3, '0')}`
  }

  toVTTString() {
    return `${String(this.hours).padStart(2, '0')}:${String(this.minutes).padStart(2, '0')}:${String(this.seconds).padStart(2, '0')}.${String(this.milliseconds).padStart(3, '0')}`
  }

  toDisplayString() {
    return `${String(this.hours).padStart(2, '0')}:${String(this.minutes).padStart(2, '0')}:${String(this.seconds).padStart(2, '0')}.${String(this.milliseconds).padStart(3, '0')}`
  }
}

export class Paragraph {
  constructor(startTime, endTime, text, number = 0) {
    this.id = this.generateId()
    this.number = number
    this.startTime = startTime instanceof TimeCode ? startTime : new TimeCode(startTime)
    this.endTime = endTime instanceof TimeCode ? endTime : new TimeCode(endTime)
    this.text = text || ''
    this.translation = ''
    this.style = ''
    this.actor = ''
    this.marginL = '0000'
    this.marginR = '0000'
    this.marginV = '0000'
    this.effect = ''
    this.isComment = false
    this.forced = false
  }

  generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }

  get duration() {
    return new TimeCode(this.endTime.totalMilliseconds - this.startTime.totalMilliseconds)
  }

  clone() {
    const p = new Paragraph(
      new TimeCode(this.startTime.totalMilliseconds),
      new TimeCode(this.endTime.totalMilliseconds),
      this.text,
      this.number
    )
    p.id = this.id
    p.translation = this.translation
    p.style = this.style
    p.actor = this.actor
    p.marginL = this.marginL
    p.marginR = this.marginR
    p.marginV = this.marginV
    p.effect = this.effect
    p.isComment = this.isComment
    p.forced = this.forced
    return p
  }
}

export class Subtitle {
  constructor() {
    this.paragraphs = []
    this.header = ''
    this.footer = ''
    this.fileName = 'Untitled'
    this.originalFormat = null
    this.historyItems = []
    this.redoItems = []
    this.maxHistoryItems = 100
  }

  get canUndo() {
    return this.historyItems.length > 0
  }

  get canRedo() {
    return this.redoItems.length > 0
  }

  addParagraph(paragraph) {
    this.paragraphs.push(paragraph)
    this.renumber()
  }

  insertParagraph(index, paragraph) {
    this.paragraphs.splice(index, 0, paragraph)
    this.renumber()
  }

  removeParagraph(index) {
    if (index >= 0 && index < this.paragraphs.length) {
      this.paragraphs.splice(index, 1)
      this.renumber()
    }
  }

  updateParagraph(index, paragraph) {
    if (index >= 0 && index < this.paragraphs.length) {
      this.paragraphs[index] = paragraph
    }
  }

  getParagraph(index) {
    return this.paragraphs[index] || null
  }

  renumber() {
    for (let i = 0; i < this.paragraphs.length; i++) {
      this.paragraphs[i].number = i + 1
    }
  }

  sort() {
    this.paragraphs.sort((a, b) => a.startTime.totalMilliseconds - b.startTime.totalMilliseconds)
    this.renumber()
  }

  saveHistory(description) {
    const historyItem = {
      description: description,
      timestamp: new Date(),
      paragraphs: this.paragraphs.map(p => p.clone())
    }
    this.historyItems.push(historyItem)
    if (this.historyItems.length > this.maxHistoryItems) {
      this.historyItems.shift()
    }
    // 新编辑使重做栈失效
    this.redoItems = []
  }

  undo() {
    if (this.historyItems.length > 0) {
      const historyItem = this.historyItems.pop()
      // 当前状态进入重做栈
      this.redoItems.push({
        description: historyItem.description,
        paragraphs: this.paragraphs.map(p => p.clone())
      })
      this.paragraphs = historyItem.paragraphs
      return true
    }
    return false
  }

  redo() {
    if (this.redoItems.length > 0) {
      const item = this.redoItems.pop()
      // 回退前的状态回到历史栈,保证再撤销能回到该状态
      this.historyItems.push({
        description: item.description,
        timestamp: new Date(),
        paragraphs: this.paragraphs.map(p => p.clone())
      })
      this.paragraphs = item.paragraphs
      return true
    }
    return false
  }

  clear() {
    this.paragraphs = []
    this.header = ''
    this.footer = ''
    this.historyItems = []
    this.redoItems = []
  }

  // ============================================================
  // 历史栈序列化(限条数,避免 .stproj 过大)
  // ============================================================
  static paragraphToPlain(p) {
    return {
      start: p.startTime.totalMilliseconds,
      end: p.endTime.totalMilliseconds,
      text: p.text,
      translation: p.translation || '',
      style: p.style || '',
      actor: p.actor || '',
      marginL: p.marginL || '0000',
      marginR: p.marginR || '0000',
      marginV: p.marginV || '0000',
      effect: p.effect || '',
      isComment: !!p.isComment,
      forced: !!p.forced,
      id: p.id,
      number: p.number || 0
    }
  }

  static paragraphFromPlain(obj) {
    const p = new Paragraph(
      new TimeCode(obj.start || 0),
      new TimeCode(obj.end || 0),
      obj.text || '',
      obj.number || 0
    )
    if (obj.id) p.id = obj.id
    p.translation = obj.translation || ''
    p.style = obj.style || ''
    p.actor = obj.actor || ''
    p.marginL = obj.marginL || '0000'
    p.marginR = obj.marginR || '0000'
    p.marginV = obj.marginV || '0000'
    p.effect = obj.effect || ''
    p.isComment = !!obj.isComment
    p.forced = !!obj.forced
    return p
  }

  serializeHistory(maxItems = 30) {
    const slice = (arr) => arr.slice(Math.max(0, arr.length - maxItems)).map(item => ({
      description: item.description,
      timestamp: item.timestamp instanceof Date ? item.timestamp.toISOString() : (item.timestamp || null),
      paragraphs: (item.paragraphs || []).map(Subtitle.paragraphToPlain)
    }))
    return {
      undo: slice(this.historyItems),
      redo: slice(this.redoItems)
    }
  }

  restoreHistory(history) {
    if (!history) return
    const parseStack = (arr) => Array.isArray(arr) ? arr.map(item => ({
      description: item.description,
      timestamp: item.timestamp ? new Date(item.timestamp) : new Date(),
      paragraphs: (item.paragraphs || []).map(Subtitle.paragraphFromPlain)
    })) : []
    this.historyItems = parseStack(history.undo)
    this.redoItems = parseStack(history.redo)
    if (this.historyItems.length > this.maxHistoryItems) {
      this.historyItems = this.historyItems.slice(-this.maxHistoryItems)
    }
  }
}

export class SubtitleFormats {
  static parseSRT(content) {
    const subtitle = new Subtitle()
    const lines = content.split(/\r?\n/)
    let currentParagraph = null
    let expecting = 'number'
    let textLines = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      
      if (line === '') {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join('\n')
          subtitle.addParagraph(currentParagraph)
          currentParagraph = null
          textLines = []
          expecting = 'number'
        }
        continue
      }

      if (expecting === 'number') {
        const num = parseInt(line, 10)
        if (!isNaN(num)) {
          currentParagraph = new Paragraph(new TimeCode(), new TimeCode(), '', num)
          expecting = 'timecode'
        }
      } else if (expecting === 'timecode') {
        const match = line.match(/(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})/)
        if (match) {
          currentParagraph.startTime = TimeCode.parse(match[1].replace(',', '.'))
          currentParagraph.endTime = TimeCode.parse(match[2].replace(',', '.'))
          expecting = 'text'
        }
      } else if (expecting === 'text') {
        textLines.push(line)
      }
    }

    if (currentParagraph && textLines.length > 0) {
      currentParagraph.text = textLines.join('\n')
      subtitle.addParagraph(currentParagraph)
    }

    return subtitle
  }

  static parseVTT(content) {
    const subtitle = new Subtitle()
    const lines = content.split(/\r?\n/)
    let currentParagraph = null
    let expecting = 'header'
    let textLines = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      if (expecting === 'header') {
        if (line.startsWith('WEBVTT')) {
          subtitle.header = line
          expecting = 'timecode'
          continue
        }
        if (line.trim() === '') {
          expecting = 'timecode'
          continue
        }
        continue
      }

      if (line.trim() === '') {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join('\n')
          subtitle.addParagraph(currentParagraph)
          currentParagraph = null
          textLines = []
        }
        continue
      }

      const timeMatch = line.match(/(\d{1,2}:?\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{1,2}:?\d{2}:\d{2}\.\d{3})/)
      if (timeMatch) {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join('\n')
          subtitle.addParagraph(currentParagraph)
          textLines = []
        }
        currentParagraph = new Paragraph(
          TimeCode.parse(timeMatch[1]),
          TimeCode.parse(timeMatch[2]),
          ''
        )
        continue
      }

      if (currentParagraph) {
        textLines.push(line)
      }
    }

    if (currentParagraph && textLines.length > 0) {
      currentParagraph.text = textLines.join('\n')
      subtitle.addParagraph(currentParagraph)
    }

    return subtitle
  }

  static toSRT(subtitle, useTranslation = false) {
    let output = ''
    for (const p of subtitle.paragraphs) {
      output += `${p.number}\n`
      output += `${p.startTime.toSRTString()} --> ${p.endTime.toSRTString()}\n`
      output += `${useTranslation ? (p.translation || p.text) : p.text}\n\n`
    }
    return output.trim() + '\n'
  }

  static toSRTTranslation(subtitle) {
    return SubtitleFormats.toSRT(subtitle, true)
  }

  static toVTT(subtitle) {
    let output = 'WEBVTT\n\n'
    for (const p of subtitle.paragraphs) {
      output += `${p.startTime.toVTTString()} --> ${p.endTime.toVTTString()}\n`
      output += `${p.text}\n\n`
    }
    return output.trim() + '\n'
  }

  static parseASS(content) {
    const subtitle = new Subtitle()
    const lines = content.split(/\r?\n/)
    let currentParagraph = null
    let inEvents = false

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()

      if (line === '[Events]') {
        inEvents = true
        continue
      }

      if (!inEvents) continue

      if (line.startsWith('Dialogue:')) {
        const parts = line.substring(9).split(',')
        if (parts.length >= 10) {
          const start = parts[1].trim()
          const end = parts[2].trim()
          const style = parts[3].trim()
          const name = parts[4].trim()
          const marginL = parts[5].trim()
          const marginR = parts[6].trim()
          const marginV = parts[7].trim()
          const effect = parts[8].trim()
          const text = parts.slice(9).join(',').trim()

          const parseTime = (timeStr) => {
            const timeParts = timeStr.split(':')
            if (timeParts.length === 3) {
              const [hours, minutes, seconds] = timeParts
              const [sec, ms] = seconds.split('.')
              return new TimeCode(
                parseInt(hours) * 3600000 +
                parseInt(minutes) * 60000 +
                parseInt(sec) * 1000 +
                parseInt(ms.padEnd(3, '0'))
              )
            }
            return new TimeCode()
          }

          currentParagraph = new Paragraph(
            parseTime(start),
            parseTime(end),
            text
          )
          currentParagraph.style = style
          currentParagraph.actor = name
          currentParagraph.marginL = marginL
          currentParagraph.marginR = marginR
          currentParagraph.marginV = marginV
          currentParagraph.effect = effect
          subtitle.addParagraph(currentParagraph)
        }
      }
    }

    return subtitle
  }

  static parseTXT(content) {
    const subtitle = new Subtitle()
    const lines = content.split(/\r?\n/)
    let currentParagraph = null
    let textLines = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()

      if (line === '') {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join(' ')
          subtitle.addParagraph(currentParagraph)
          currentParagraph = null
          textLines = []
        }
        continue
      }

      const timeMatch = line.match(/(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-+\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})/)
      if (timeMatch) {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join(' ')
          subtitle.addParagraph(currentParagraph)
          textLines = []
        }
        currentParagraph = new Paragraph(
          TimeCode.parse(timeMatch[1].replace(',', '.')),
          TimeCode.parse(timeMatch[2].replace(',', '.')),
          ''
        )
      } else if (currentParagraph) {
        textLines.push(line)
      }
    }

    if (currentParagraph && textLines.length > 0) {
      currentParagraph.text = textLines.join(' ')
      subtitle.addParagraph(currentParagraph)
    }

    return subtitle
  }

  static parseSMI(content) {
    const subtitle = new Subtitle()
    const lines = content.split(/\r?\n/)
    let currentParagraph = null
    let inSync = false
    let textLines = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]

      if (line.match(/<SYNC Start="(\d+)"/)) {
        if (currentParagraph && textLines.length > 0) {
          currentParagraph.text = textLines.join('').replace(/<[^>]+>/g, '').trim()
          subtitle.addParagraph(currentParagraph)
          textLines = []
        }
        const start = parseInt(line.match(/<SYNC Start="(\d+)"/)[1])
        currentParagraph = new Paragraph(
          new TimeCode(start),
          new TimeCode(start + 3000),
          ''
        )
        inSync = true
      } else if (inSync && line.match(/<\/SYNC>/)) {
        inSync = false
      } else if (inSync && currentParagraph) {
        textLines.push(line)
      }
    }

    if (currentParagraph && textLines.length > 0) {
      currentParagraph.text = textLines.join('').replace(/<[^>]+>/g, '').trim()
      subtitle.addParagraph(currentParagraph)
    }

    return subtitle
  }

  static toASS(subtitle) {
    let output = "[Script Info]\n"
    output += "Title: Subtitle\n"
    output += "ScriptType: v4.00+\n"
    output += "Collisions: Normal\n"
    output += "PlayResX: 1920\n"
    output += "PlayResY: 1080\n"
    output += "Timer: 100.0000\n"
    output += "WrapStyle: 0\n"
    output += "ScaledBorderAndShadow: yes\n"
    output += "YCbCr Matrix: None\n\n"

    output += "[V4+ Styles]\n"
    output += "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
    output += "Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1\n\n"

    output += "[Events]\n"
    output += "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"

    for (const p of subtitle.paragraphs) {
      const start = `${p.startTime.hours}:${String(p.startTime.minutes).padStart(2, '0')}:${String(p.startTime.seconds).padStart(2, '0')}.${String(p.startTime.milliseconds).padStart(2, '0')}`
      const end = `${p.endTime.hours}:${String(p.endTime.minutes).padStart(2, '0')}:${String(p.endTime.seconds).padStart(2, '0')}.${String(p.endTime.milliseconds).padStart(2, '0')}`
      output += `Dialogue: 0,${start},${end},${p.style || 'Default'},${p.actor || ''},${p.marginL},${p.marginR},${p.marginV},${p.effect || ''},${p.text}\n`
    }

    return output
  }

  static toTXT(subtitle) {
    let output = ''
    for (const p of subtitle.paragraphs) {
      output += `${p.startTime.toSRTString().replace(',', '.')} -- ${p.endTime.toSRTString().replace(',', '.')}\n`
      output += `${p.text}\n\n`
    }
    return output.trim() + '\n'
  }

  static detectFormat(content) {
    if (content.startsWith('WEBVTT')) {
      return 'vtt'
    }
    if (content.match(/^\d+\s*\n\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}/m)) {
      return 'srt'
    }
    if (content.match(/\[Script Info\]/i)) {
      return 'ass'
    }
    if (content.match(/<SYNC Start="\d+"/)) {
      return 'smi'
    }
    if (content.match(/\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s*-+\s*\d{1,2}:\d{2}:\d{2}[,.]\d{3}/)) {
      return 'txt'
    }
    return null
  }

  static parse(content, format = null) {
    if (!format) {
      format = this.detectFormat(content)
    }
    
    switch (format) {
      case 'vtt':
        return this.parseVTT(content)
      case 'ass':
        return this.parseASS(content)
      case 'smi':
        return this.parseSMI(content)
      case 'txt':
        return this.parseTXT(content)
      case 'srt':
      default:
        return this.parseSRT(content)
    }
  }
}
