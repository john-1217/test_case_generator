<script setup lang="ts">
// 检索测试页：业务知识库问答（BM25 检索 + LLM 流式生成 + 命中块溯源）
// 索引来自 /api/v1/retrieval-test/chunks（chunk-all.mjs 生成），BM25 在浏览器内构建
import { computed, nextTick, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { llmConfigService } from '../services/api'

interface Chunk {
  id: string
  source: string
  layer: string | null
  domain: string | null
  doc_title: string
  section_path: string | null
  chunk_type: string
  char_len: number
  doc_version: string | null
  updated_at: string | null
  collection: string
  context_prefix: string
  content: string
}

interface ModelGroup { provider: string; name: string; models: string[] }

interface Hit extends Chunk { score: number; html: string }

const messages = ref<any[]>([])
const input = ref('')
const hits = ref<Hit[]>([])
const stats = ref<{ totalChunks: number; totalDocs: number } | null>(null)
const searching = ref(false)
const collections = ref<string[]>(['business', 'business-doc'])
const collectionOptions = [
  { value: 'business', label: '业务知识' },
  { value: 'business-doc', label: '操作手册' },
  { value: 'meta', label: '建设元文档' },
  { value: 'skill', label: 'Skill' },
]
const quickAsks = [
  '订单预览时优惠券查询失败会阻断吗',
  '帮买预约时间规则',
  '订单金额上限是多少',
  '小程序预览和MRN的差异',
]
const msgsEl = ref<HTMLElement>()

// LLM 选择（复用「模型配置」里已配置的厂商与模型，仅展示文本模型，语音/向量等模型过滤掉）
interface ModelGroup { provider: string; name: string; models: string[] }

const NON_TEXT_MODEL_RE = /speech|tts|asr|whisper|audio|voice|embedding|rerank|image|video|moderation|vision/i
const modelGroups = ref<ModelGroup[]>([])
const selectedModelKey = ref(localStorage.getItem('rt-model-key') || '') // 格式: "provider|model"
const textGroups = computed(() =>
  modelGroups.value
    .map(g => ({ ...g, models: g.models.filter(m => !NON_TEXT_MODEL_RE.test(m)) }))
    .filter(g => g.models.length > 0)
)
const llmReady = computed(() => selectedModelKey.value.includes('|'))

function parseModelKey(): { provider: string; model: string } {
  const [provider, ...rest] = selectedModelKey.value.split('|')
  return { provider, model: rest.join('|') }
}

function onModelChange() {
  localStorage.setItem('rt-model-key', selectedModelKey.value)
}

// ---------- 分词：ASCII 词 + 中文 bigram ----------
function tokenize(text: string): string[] {
  const toks: string[] = []
  for (const w of text.toLowerCase().match(/[a-z0-9_.]+/g) || []) toks.push(w)
  const cjk = (text.match(/[\u4e00-\u9fff]/g) || []).join('')
  for (let i = 0; i < cjk.length - 1; i++) toks.push(cjk[i] + cjk[i + 1])
  if (cjk.length === 1) toks.push(cjk)
  return toks
}
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

// ---------- BM25 ----------
const BM25: any = {
  docs: [] as any[], postings: new Map<string, number[]>(), idf: new Map<string, number>(), avgLen: 0, k1: 1.5, b: 0.75,
  add(rec: Chunk) {
    const toks = tokenize(rec.content)
    const tf = new Map<string, number>()
    for (const t of toks) tf.set(t, (tf.get(t) || 0) + 1)
    const di = this.docs.length
    this.docs.push({ rec, len: toks.length, tf })
    for (const [t] of tf) {
      if (!this.postings.has(t)) this.postings.set(t, [])
      this.postings.get(t)!.push(di)
    }
  },
  finish() {
    this.avgLen = this.docs.reduce((s: number, d: any) => s + d.len, 0) / this.docs.length
    for (const [t, pl] of this.postings) {
      this.idf.set(t, Math.log(1 + (this.docs.length - pl.length + 0.5) / (pl.length + 0.5)))
    }
  },
  search(query: string, allow: Set<string>, topK = 8): Hit[] {
    const qToks = [...new Set(tokenize(query))]
    const scores = new Map<number, number>()
    for (const qt of qToks) {
      const idf = this.idf.get(qt)
      if (idf === undefined) continue
      for (const di of this.postings.get(qt) || []) {
        const d = this.docs[di]
        if (!allow.has(d.rec.collection)) continue
        const tf = d.tf.get(qt)!
        const s = idf * (tf * (this.k1 + 1)) / (tf + this.k1 * (1 - this.b + this.b * d.len / this.avgLen))
        scores.set(di, (scores.get(di) || 0) + s)
      }
    }
    return [...scores.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, topK)
      .map(([di, score]) => ({ ...this.docs[di].rec, score, html: '' }))
  },
}

// ---------- 抽取式兜底回答 ----------
function extractSentences(hitsArr: Hit[], query: string, max = 6) {
  const qToks = new Set(tokenize(query))
  const cands: any[] = []
  hitsArr.slice(0, 5).forEach((h, hi) => {
    const body = h.content.split('\n').slice(2).join('\n')
    for (let line of body.split('\n')) {
      line = line.trim()
      if (!line || line === '---' || line.startsWith('|---') || line.startsWith('```') || /^flowchart|subgraph|end$/.test(line)) continue
      for (let sent of line.split(/(?<=[。！？；])/)) {
        sent = sent.trim().replace(/^[-*|>\s]+/, '').replace(/\|/g, ' ')
        if (sent.length < 12 || sent.length > 220) continue
        const toks = new Set(tokenize(sent))
        let sc = 0
        for (const qt of qToks) if (toks.has(qt)) sc += BM25.idf.get(qt) || 0
        if (sc <= 0) continue
        cands.push({ ref: hi, from: h.doc_title + (h.section_path ? ' · ' + h.section_path : ''), text: sent, norm: sc / Math.sqrt(sent.length) })
      }
    }
  })
  cands.sort((a, b) => b.norm - a.norm)
  const picked: any[] = []
  for (const c of cands) {
    const t = new Set(tokenize(c.text))
    const dup = picked.some(p => {
      const pt = new Set(tokenize(p.text))
      let ov = 0; for (const x of t) if (pt.has(x)) ov++
      return ov / Math.max(1, Math.min(t.size, pt.size)) > 0.7
    })
    if (dup) continue
    if (picked.filter(x => x.ref === c.ref).length >= 2) continue
    picked.push(c)
    if (picked.length >= max) break
  }
  picked.sort((a, b) => a.ref - b.ref)
  return picked.map(p => ({ ...p, html: esc(p.text) }))
}

// ---------- LLM 流式回答 ----------
const SYS_PROMPT = '你是业务知识库问答助手。只能依据用户消息中提供的知识块回答问题，不得编造；回答简明分点，引用知识块时在句末标注来源编号如【1】；若知识块不足以回答，明确说明"知识库未覆盖该问题"，并指出最接近的相关信息。'

function renderAnswer(text: string) {
  return esc(text || '').replace(/【(\d{1,2})】/g, '<span class="cite">【$1】</span>')
}

async function askLLM(query: string, top: Hit[], msg: any) {
  msg.streaming = true
  msg.answer = ''
  const ctx = top.slice(0, 8).map((h, i) =>
    `【${i + 1}】来源: ${h.doc_title}${h.section_path ? ' · ' + h.section_path : ''}（${h.source}）\n${h.content.split('\n').slice(2).join('\n').slice(0, 2500)}`
  ).join('\n\n---\n\n')
  const body = {
    ...parseModelKey(),
    messages: [
      { role: 'system', content: SYS_PROMPT },
      { role: 'user', content: `问题：${query}\n\n知识块：\n${ctx}` },
    ],
  }
  const res = await fetch('/api/v1/retrieval-test/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
    body: JSON.stringify(body),
  })
  if (!res.ok || !res.body) throw new Error((await res.text().catch(() => '')).slice(0, 300) || `HTTP ${res.status}`)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += dec.decode(value, { stream: true })
    let nl
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim()
      buf = buf.slice(nl + 1)
      if (!line.startsWith('data:')) continue
      const data = line.slice(5).trim()
      if (data === '[DONE]') { msg.streaming = false; return }
      try {
        const j = JSON.parse(data)
        if (j.error) throw new Error(j.error)
        const delta = j.choices?.[0]?.delta?.content
        if (delta) { msg.answer += delta; scrollBottom() }
      } catch (e: any) {
        if (e instanceof SyntaxError) continue
        msg.error = 'LLM 返回错误: ' + e.message
        msg.streaming = false
        return
      }
    }
  }
  msg.streaming = false
}

function scrollBottom() {
  nextTick(() => { if (msgsEl.value) msgsEl.value.scrollTop = msgsEl.value.scrollHeight })
}

async function boot() {
  const res = await fetch('/api/v1/retrieval-test/chunks')
  if (!res.ok) { ElMessage.error('知识块索引加载失败，请确认 backend/data/retrieval/chunks.jsonl 存在'); return }
  const text = await res.text()
  const docSet = new Set<string>()
  let kept = 0
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    const rec: Chunk = JSON.parse(line)
    docSet.add(rec.source)
    if (rec.char_len > 20000) continue
    BM25.add(rec); kept++
  }
  BM25.finish()
  stats.value = { totalChunks: kept, totalDocs: docSet.size }
  try {
    modelGroups.value = await llmConfigService.getModelGroups()
  } catch { /* 未登录或无配置时忽略 */ }
}
onMounted(boot)

function ask(q?: string) {
  const query = (q ?? input.value).trim()
  if (!query || searching.value) return
  input.value = ''
  messages.value.push({ role: 'user', text: query })
  searching.value = true
  setTimeout(() => {
    const top: Hit[] = BM25.search(query, new Set(collections.value), 8)
    hits.value = top.map(h => ({ ...h, html: esc(h.content.split('\n').slice(2).join('\n')) }))
    if (llmReady.value && top.length) {
      const { model } = parseModelKey()
      messages.value.push({ role: 'bot', hits: top, answer: '', model })
      // 取数组里的响应式代理再传给流式函数；直接改原始对象不会触发 Vue 更新
      const msg = messages.value[messages.value.length - 1]
      askLLM(query, top, msg).catch((e: Error) => {
        msg.error = 'LLM 调用失败: ' + e.message
        msg.extracted = extractSentences(top, query)
        msg.streaming = false
      })
    } else {
      messages.value.push({ role: 'bot', hits: top, extracted: extractSentences(top, query) })
    }
    searching.value = false
    scrollBottom()
  }, 120)
}

function jumpTo(refIdx: number) {
  const el = document.getElementById('hit-' + refIdx)
  if (el) { el.scrollIntoView({ behavior: 'smooth' }); el.style.borderColor = '#409eff'; setTimeout(() => (el.style.borderColor = ''), 1500) }
}
</script>

<template>
  <div class="rt-page">
    <div class="rt-toolbar">
      <span class="rt-title">检索测试</span>
      <span class="rt-sub" v-if="stats">索引 {{ stats.totalChunks }} 块 / {{ stats.totalDocs }} 文档 · BM25 检索 · {{ llmReady ? 'LLM 生成回答' : '抽取式回答（选择模型后生效）' }}</span>
      <el-checkbox-group v-model="collections" size="small" class="rt-collections">
        <el-checkbox-button v-for="c in collectionOptions" :key="c.value" :value="c.value">{{ c.label }}</el-checkbox-button>
      </el-checkbox-group>
      <div class="rt-llm">
        <el-select v-model="selectedModelKey" placeholder="选择文本模型（来自模型配置）" size="small" filterable style="width: 260px" @change="onModelChange">
          <el-option-group v-for="g in textGroups" :key="g.provider" :label="g.name">
            <el-option v-for="m in g.models" :key="g.provider + '|' + m" :label="m" :value="g.provider + '|' + m" />
          </el-option-group>
        </el-select>
      </div>
    </div>

    <div class="rt-main">
      <section class="chat-pane">
        <div class="msgs" ref="msgsEl">
          <div class="msg bot" v-if="messages.length === 0">
            <div class="bubble">
              知识库已就绪。输入业务问题试试，比如：<br>
              · 订单预览时优惠券查询失败会阻断吗？<br>
              · 帮买预约时间规则是什么？
              <div class="src-line">右侧面板展示命中的知识块，可展开原文并跳转源文件。</div>
            </div>
          </div>
          <div class="msg" v-for="(m, i) in messages" :key="i" :class="m.role">
            <div class="bubble">
              <template v-if="m.role === 'user'">{{ m.text }}</template>
              <template v-else>
                <div v-if="m.error" class="rt-error">{{ m.error }}（降级为抽取式回答）</div>
                <div v-if="m.answer !== undefined">
                  <div class="answer" v-html="renderAnswer(m.answer)"></div>
                  <div v-if="m.streaming" class="rt-loading">生成中…</div>
                  <div class="src-line" v-if="!m.streaming && !m.error">由 {{ m.model }} 基于右侧 {{ (m.hits || []).length }} 个知识块生成</div>
                </div>
                <template v-else>
                  <div v-if="m.hits && m.hits.length">根据知识库检索，命中的关键原文：</div>
                  <div v-else>知识库中未检索到相关内容（可尝试换关键词，或放开上方集合过滤）。</div>
                  <ul>
                    <li v-for="(s, si) in m.extracted" :key="si">
                      <span class="cite" @click="jumpTo(s.ref)">【{{ s.ref + 1 }}】</span>
                      <span v-html="s.html"></span>
                      <span class="src-line"> —— {{ s.from }}</span>
                    </li>
                  </ul>
                </template>
              </template>
            </div>
          </div>
        </div>
        <div class="input-bar">
          <div class="quick-asks">
            <el-tag v-for="q in quickAsks" :key="q" style="cursor: pointer" effect="plain" size="small" @click="ask(q)">{{ q }}</el-tag>
          </div>
          <div class="input-row">
            <el-input v-model="input" placeholder="输入业务问题，Enter 发送…" @keydown.enter.exact.prevent="ask()" clearable />
            <el-button type="primary" @click="ask()" :loading="searching">发送</el-button>
          </div>
        </div>
      </section>

      <aside class="retrieval-pane">
        <div class="pane-title">检索命中的知识块（{{ hits.length }}）</div>
        <div class="hit-list">
          <el-empty v-if="!hits.length" description="提问后展示命中块" />
          <div class="hit" v-for="(h, i) in hits" :key="h.id" :id="'hit-' + i">
            <div class="h-head">
              <span class="score">#{{ i + 1 }} score {{ h.score.toFixed(2) }}</span>
              <span class="crumb">{{ h.doc_title }}<template v-if="h.section_path"> · {{ h.section_path }}</template></span>
            </div>
            <div class="h-meta">
              <el-tag size="small">{{ h.collection }}</el-tag>
              <el-tag size="small" type="info">{{ h.layer || '—' }}</el-tag>
              <el-tag size="small" type="warning">{{ h.chunk_type }}</el-tag>
              <span>{{ h.char_len }}字符</span>
              <span v-if="h.doc_version">{{ h.doc_version }} · {{ h.updated_at }}</span>
            </div>
            <pre>{{ h.content.split('\n').slice(2).join('\n') }}</pre>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.rt-page { display: flex; flex-direction: column; height: calc(100vh - 64px - 68px); min-height: 480px; }
.rt-toolbar { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: var(--color-surface, #fff); border: 1px solid var(--color-border, #e4e7ed); border-radius: 10px; flex-wrap: wrap; }
.rt-title { font-weight: 700; font-size: 15px; }
.rt-sub { color: #909399; font-size: 12px; }
.rt-collections { margin-left: auto; }
.rt-llm { display: flex; gap: 8px; }
.rt-main { flex: 1; display: flex; gap: 12px; margin-top: 12px; overflow: hidden; }
.chat-pane { flex: 1.2; display: flex; flex-direction: column; border: 1px solid var(--color-border, #e4e7ed); border-radius: 10px; background: #f5f7fa; overflow: hidden; }
.msgs { flex: 1; overflow-y: auto; padding: 16px; }
.msg { margin-bottom: 14px; display: flex; }
.msg.user { justify-content: flex-end; }
.bubble { max-width: 82%; padding: 10px 14px; border-radius: 10px; font-size: 14px; line-height: 1.7; }
.msg.user .bubble { background: #409eff; color: #fff; border-top-right-radius: 2px; }
.msg.bot .bubble { background: #fff; border: 1px solid var(--color-border, #e4e7ed); border-top-left-radius: 2px; }
.cite { color: #409eff; cursor: pointer; font-size: 12px; }
.src-line { margin-top: 6px; font-size: 12px; color: #909399; }
.bubble ul { margin: 4px 0 0 0; padding-left: 4px; list-style: none; }
.bubble li { margin-bottom: 8px; padding-left: 20px; text-indent: -20px; }
.answer { white-space: pre-wrap; }
.rt-error { color: #f56c6c; margin-bottom: 8px; font-size: 13px; }
.rt-loading { color: #909399; font-size: 12px; }
.input-bar { padding: 12px; background: var(--color-surface, #fff); border-top: 1px solid var(--color-border, #e4e7ed); flex-shrink: 0; }
.quick-asks { margin-bottom: 8px; display: flex; gap: 6px; flex-wrap: wrap; }
.input-row { display: flex; gap: 8px; }
.retrieval-pane { width: 440px; flex-shrink: 0; display: flex; flex-direction: column; border: 1px solid var(--color-border, #e4e7ed); border-radius: 10px; background: var(--color-surface, #fff); overflow: hidden; }
.pane-title { padding: 12px 14px; font-size: 14px; font-weight: 600; border-bottom: 1px solid var(--color-border, #e4e7ed); }
.hit-list { flex: 1; overflow-y: auto; padding: 12px; }
.hit { border: 1px solid var(--color-border, #e4e7ed); border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; background: #fafafa; }
.h-head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
.score { font-size: 12px; color: #e6a23c; font-weight: 600; }
.crumb { font-size: 13px; font-weight: 600; }
.h-meta { font-size: 12px; color: #909399; margin-bottom: 6px; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.hit pre { margin: 0; white-space: pre-wrap; font-size: 12px; line-height: 1.6; color: #606266; max-height: 240px; overflow-y: auto; background: #fff; padding: 8px; border-radius: 6px; border: 1px solid #ebeef5; }
</style>
