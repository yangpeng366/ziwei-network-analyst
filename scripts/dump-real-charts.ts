/**
 * Dump real charts from v4 birth keys via upstream generateChart.
 * Run from ziwei-doushu root:
 *   npx tsx F:/github/ziwei-network-analyst/scripts/dump-real-charts.ts
 */
import { createReadStream, writeFileSync, mkdirSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { generateChart } from '../lib/ziwei/algorithm.ts';

type Row = {
  k: string;
  y: number;
  m: number;
  d: number;
  h: number;
  g: 'male' | 'female';
  ms?: string;
  t: Record<string, number>;
  c: Record<string, string>;
};

const CORPUS = 'F:/github/ziwei-network-analyst/data/v4-sample/year-1990.jsonl';
const OUT_DIR = 'F:/github/ziwei-network-analyst/fixtures/real-1990';
const SAMPLE_N = 36;

function softCommunityScore(c: Record<string, string>): { score: number; hits: string[] } {
  const love = typeof c.love === 'string' ? c.love : '';
  const friends = typeof c.friends === 'string' ? c.friends : '';
  const move = typeof c.move === 'string' ? c.move : '';
  const text = `${love}\n${friends}\n${move}`;
  const pos = ['人缘', '贵人', '合作', '朋友多', '人脉', '和谐', '得助', '社交', '人气', '群'];
  const neg = ['孤独', '隔阂', '不合', '离别', '难相处', '人际差', '孤立', '争吵', '防人', '冷淡'];
  let p = 0;
  let n = 0;
  const hits: string[] = [];
  for (const w of pos) if (text.includes(w)) { p += 1; hits.push('+' + w); }
  for (const w of neg) if (text.includes(w)) { n += 1; hits.push('-' + w); }
  const score = (p + 0.2) / (p + n + 0.4);
  return { score: Math.max(0, Math.min(1, score)), hits: hits.slice(0, 12) };
}

async function sampleRows(): Promise<Row[]> {
  const buckets = new Map<number, Row[]>();
  const rl = createInterface({ input: createReadStream(CORPUS, { encoding: 'utf8' }), crlfDelay: Infinity });
  let i = 0;
  for await (const line of rl) {
    if (!line.trim()) continue;
    const row = JSON.parse(line) as Row;
    // stride sample: keep ~2 per day-hour block lightly
    if (i % 180 === 0) {
      const arr = buckets.get(row.m) || [];
      if (arr.length < 6) {
        arr.push(row);
        buckets.set(row.m, arr);
      }
    }
    i += 1;
    if ([...buckets.values()].reduce((a, b) => a + b.length, 0) >= SAMPLE_N) break;
  }
  return [...buckets.values()].flat().slice(0, SAMPLE_N);
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });
  const rows = await sampleRows();
  const index: any[] = [];
  for (const row of rows) {
    const chart = generateChart({
      year: row.y,
      month: row.m,
      day: row.d,
      hour: row.h,
      gender: row.g,
    });
    // attach soft labels only in sidecar index, not inside engine chart
    const soft = softCommunityScore(row.c || {});
    const file = `${row.k}.json`;
    writeFileSync(`${OUT_DIR}/${file}`, JSON.stringify(chart, null, 2), 'utf8');
    index.push({
      key: row.k,
      file,
      ming_star: row.ms,
      soft_community: soft.score,
      soft_hits: soft.hits,
      love_head: (typeof row.c?.love === 'string' ? row.c.love : '').slice(0, 80),
      friends_head: (typeof row.c?.friends === 'string' ? row.c.friends : '').slice(0, 80),
    });
    console.log('dumped', row.k, 'soft', soft.score.toFixed(3));
  }
  writeFileSync(`${OUT_DIR}/index.json`, JSON.stringify(index, null, 2), 'utf8');
  console.log('wrote', index.length, 'charts to', OUT_DIR);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});