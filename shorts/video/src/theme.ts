/** 색·글꼴·크기 토큰. 장면 파일은 여기 값만 쓴다. 특정 회사·브랜드 색은 넣지 않는다. */
import {loadFont} from '@remotion/google-fonts/NotoSansKR';

// 렌더할 때 Google Fonts에서 받는다. 한글은 글자 구간별 파일이 많아 요청 수 경고를 끈다.
const {fontFamily} = loadFont('normal', {weights: ['500', '700', '900'], ignoreTooManyRequestsWarning: true});

export const FONT = fontFamily;

export const WIDTH = 1080;
export const HEIGHT = 1920;
export const FPS = 30;

export const color = {
  bg: '#F6F5F1',
  surface: '#FFFFFF',
  ink: '#15171C',
  inkSoft: '#5B606B',
  line: '#E2E0D8',
  accent: '#2F62E0',
  accentSoft: '#E3EAFC',
  /** "우리 해석" 표시 */
  interp: '#B45309',
  interpSoft: '#FEF3E2',
  /** "예시값, 예측치 아님" 같은 주의 표시 */
  caution: '#9A3412',
  captionBg: 'rgba(21, 23, 28, 0.86)',
  captionInk: '#FFFFFF',
  captionActive: '#FFD54A',
};

export const size = {
  gutter: 84,
  headline: 92,
  line: 64,
  number: 200,
  chip: 40,
  caption: 54,
  footer: 30,
};

/** 화면 첫 줄 표시 문구. verify.py와 같아야 한다. */
export const INTERPRETATION_LABEL = '우리 해석';
export const ILLUSTRATIVE_LABEL = '예시값';
