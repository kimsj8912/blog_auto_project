/** 2단계 storyboard.json과 3단계 voice.json을 합친 영상 입력. */

export type Purpose = 'hook' | 'context' | 'point' | 'interpretation' | 'closing';

export type Word = {text: string; start: number; end: number};

export type ScreenNumber = {display: string; source_number_id: string; is_illustrative: boolean};

export type SceneData = {
  index: number;
  purpose: Purpose;
  narration: string;
  on_screen_text: string[];
  numbers: ScreenNumber[];
  visual_intent: string;
  /** 음성 파일(실행 폴더 기준 경로) */
  audio: string;
  /** 장면 시작 → 말 시작(초) */
  speechStart: number;
  audioSeconds: number;
  /** 장면 전체 길이(초) = 말 시작 전 여백 + 음성 + 끝난 뒤 여백 */
  sceneSeconds: number;
  words: Word[];
};

export type RunData = {
  title: string;
  origin: string;
  scenes: SceneData[];
};

export type SceneProps = {scene: SceneData; fps: number; durationInFrames: number};
