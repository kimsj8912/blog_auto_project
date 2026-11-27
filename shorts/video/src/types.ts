/** 2단계 storyboard.json과 3단계 voice.json을 합친 영상 입력. */

export type Purpose = 'hook' | 'context' | 'point' | 'interpretation' | 'closing';

/** caption: 자막 표기(5단계). 빈 문자열이면 앞 단어에 붙어 보이지 않는다. 없으면 text를 쓴다. */
export type Word = {text: string; start: number; end: number; caption?: string};

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
  /** on_screen_text 줄마다 처음 들리는 시각(말 시작 기준 초). 못 찾은 줄은 null(5단계) */
  screenCues: (number | null)[];
};

export type RunData = {
  title: string;
  origin: string;
  scenes: SceneData[];
};

export type SceneProps = {scene: SceneData; fps: number; durationInFrames: number};
