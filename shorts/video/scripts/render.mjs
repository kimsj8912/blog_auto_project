// 실행 폴더(.local/runs/<폴더>)를 영상으로 만든다. 실행 폴더를 Remotion public 폴더로 연다.
//   npm run render -- --run-dir ../../.local/runs/<폴더>   → <폴더>/video.mp4
//   npm run stills -- --run-dir ../../.local/runs/<폴더>   → <폴더>/stills/sceneN.png (겹침 확인용)
//   npm run studio -- --run-dir ../../.local/runs/<폴더>   → 미리 보기 화면
// 크롬이 설치돼 있으면 그것을 쓰고(REMOTION_BROWSER로 바꿀 수 있음), 없으면 Remotion이 받는다.
import {spawnSync} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync} from 'node:fs';
import {join, resolve} from 'node:path';

const FPS = 30; // src/theme.ts와 같아야 한다.
const args = process.argv.slice(2);
const opt = (name) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : undefined;
};
const runArg = opt('--run-dir');
if (!runArg) {
  console.error('✗ --run-dir <실행 폴더>가 필요합니다.');
  process.exit(1);
}
const runDir = resolve(process.cwd(), runArg);
for (const f of ['storyboard.json', 'voice.json', 'source.json']) {
  if (!existsSync(join(runDir, f))) {
    console.error(`✗ ${join(runDir, f)}가 없습니다. 2단계(shorts.pipeline)와 3단계(shorts.voice)를 먼저 실행하세요.`);
    process.exit(1);
  }
}

const browser =
  process.env.REMOTION_BROWSER ??
  ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/opt/pw-browsers/chromium'].find(existsSync);
const common = ['--public-dir', runDir, ...(browser ? ['--browser-executable', browser] : [])];

const remotion = (cmd) => {
  const r = spawnSync('npx', ['remotion', ...cmd, ...common], {stdio: 'inherit'});
  if (r.status !== 0) process.exit(r.status ?? 1);
};

if (args.includes('--studio')) {
  remotion(['studio', 'src/index.ts']);
} else if (args.includes('--stills')) {
  // 장면마다 말이 70% 지난 시점(줄이 다 나오고 자막이 떠 있는 때)을 찍는다.
  const voice = JSON.parse(readFileSync(join(runDir, 'voice.json'), 'utf8'));
  const outDir = join(runDir, 'stills');
  mkdirSync(outDir, {recursive: true});
  let from = 0;
  for (const s of voice.scenes) {
    const d = Math.max(1, Math.round(s.scene_seconds * FPS));
    const frame = from + Math.round((s.speech_start + s.audio_seconds * 0.7) * FPS);
    remotion(['still', 'src/index.ts', 'Shorts', join(outDir, `scene${s.index}.png`), `--frame=${frame}`]);
    from += d;
  }
  console.log(`✓ 스틸: ${outDir}`);
} else {
  const out = join(runDir, 'video.mp4');
  remotion(['render', 'src/index.ts', 'Shorts', out]);
  console.log(`✓ 영상: ${out}`);
}
