import {staticFile} from 'remotion';
import type {Purpose, RunData, SceneData, Word} from './types';

/**
 * 실행 폴더(.local/runs/<폴더>)를 Remotion public 폴더로 열어 읽는다.
 * storyboard.json(2단계) + voice.json(3단계) + source.json(원문 주소)
 */
type Storyboard = {
  title: string;
  scenes: {
    index: number;
    purpose: Purpose;
    narration: string;
    on_screen_text: string[];
    numbers: SceneData['numbers'];
    visual_intent: string;
  }[];
};

type Voice = {
  lead_in: number;
  tail: number;
  scenes: {
    index: number;
    file: string;
    narration: string;
    audio_seconds: number;
    scene_seconds: number;
    speech_start: number;
    words: Word[];
    screen_cues?: (number | null)[];
  }[];
};

const getJson = async <T,>(name: string): Promise<T> => {
  const res = await fetch(staticFile(name));
  if (!res.ok) throw new Error(`${name}을(를) 읽지 못했습니다. 실행 폴더에 2·3단계 결과가 있는지 확인하세요.`);
  return res.json() as Promise<T>;
};

export const mergeRun = (sb: Storyboard, voice: Voice, origin: string): RunData => {
  const byIndex = new Map(voice.scenes.map((v) => [v.index, v]));
  const scenes = sb.scenes.map((s): SceneData => {
    const v = byIndex.get(s.index);
    if (!v) throw new Error(`장면 ${s.index}의 음성이 없습니다. python -m shorts.voice 를 먼저 실행하세요.`);
    if (v.narration !== s.narration) {
      throw new Error(`장면 ${s.index}의 대본이 음성과 다릅니다. 음성을 다시 만드세요(--only ${s.index}).`);
    }
    return {
      ...s,
      audio: v.file,
      speechStart: v.speech_start,
      audioSeconds: v.audio_seconds,
      sceneSeconds: v.scene_seconds,
      words: v.words,
      // 5단계 이전에 만든 voice.json에는 없다. 그때는 줄을 차례로 띄운다.
      screenCues: v.screen_cues ?? s.on_screen_text.map(() => null),
    };
  });
  return {title: sb.title, origin, scenes};
};

export const loadRun = async (): Promise<RunData> => {
  const [sb, voice, source] = await Promise.all([
    getJson<Storyboard>('storyboard.json'),
    getJson<Voice>('voice.json'),
    getJson<{origin: string}>('source.json'),
  ]);
  return mergeRun(sb, voice, source.origin);
};

/** 장면별 시작 프레임과 길이 */
export const sceneFrames = (run: RunData, fps: number) => {
  let from = 0;
  return run.scenes.map((s) => {
    const durationInFrames = Math.max(1, Math.round(s.sceneSeconds * fps));
    const item = {scene: s, from, durationInFrames};
    from += durationInFrames;
    return item;
  });
};

export const totalFrames = (run: RunData, fps: number) =>
  sceneFrames(run, fps).reduce((a, s) => a + s.durationInFrames, 0);
