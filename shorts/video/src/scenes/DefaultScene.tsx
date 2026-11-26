import React from 'react';
import {interpolate, spring, useCurrentFrame} from 'remotion';
import {ILLUSTRATIVE_LABEL, INTERPRETATION_LABEL, color, size} from '../theme';
import type {SceneProps} from '../types';

/**
 * 기본 장면: on_screen_text를 한 줄씩 띄운다.
 * - 첫 줄이 "우리 해석"이면 주황 표시로 바꾼다(원문 내용과 구분).
 * - 화면 숫자(numbers)가 든 줄은 숫자를 크게 보여 준다.
 * - "예시값"이 든 줄은 주의 표시로 보여 준다.
 * 장면마다 따로 연출하고 싶으면 scenes/ 아래에 장면 파일을 만들어 registry.ts에 등록한다.
 */

export type Line =
  | {kind: 'interp'; text: string}
  | {kind: 'caution'; text: string}
  | {kind: 'number'; number: string; before: string; after: string}
  | {kind: 'text'; text: string};

const NUMBER_TOKEN = /\d+(?:[.,]\d+)*(?:\s*[~–-]\s*\d+(?:[.,]\d+)*)?\s*(?:%|배|명|개|년|점)?/;

export const classifyLines =(lines: string[], numbers: string[]): Line[] =>
  lines.map((text, i): Line => {
    if (i === 0 && text.trim().startsWith(INTERPRETATION_LABEL)) return {kind: 'interp', text: text.trim()};
    if (text.includes(ILLUSTRATIVE_LABEL)) return {kind: 'caution', text};
    // 긴 표기부터 찾아야 '47~56%' 안의 '56%'를 먼저 잡지 않는다.
    // 화면 표기가 numbers.display와 조금 다를 수 있어(예: '47 and 56%' → '47~56%'), 장면에 숫자가
    // 등록돼 있을 때만 줄 속 숫자 모양도 찾는다. 출처 대조는 2단계 verify.py가 이미 했다.
    const hit =
      [...numbers].sort((a, b) => b.length - a.length).find((n) => n && text.includes(n)) ??
      (numbers.length ? text.match(NUMBER_TOKEN)?.[0] : undefined);
    if (hit) {
      const at = text.indexOf(hit);
      return {kind: 'number', number: hit, before: text.slice(0, at).trim(), after: text.slice(at + hit.length).trim()};
    }
    return {kind: 'text', text};
  });

const STAGGER = 10; // 줄 사이 등장 간격(프레임)

export const DefaultScene: React.FC<SceneProps> = ({scene, fps}) => {
  const frame = useCurrentFrame();
  const startAt = Math.round(scene.speechStart * fps) - 6;
  const lines = classifyLines(
    scene.on_screen_text,
    scene.numbers.map((n) => n.display),
  );
  const isInterp = lines[0]?.kind === 'interp';

  return (
    <div
      style={{
        position: 'absolute',
        left: size.gutter,
        right: size.gutter,
        top: 260,
        bottom: 520,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 36,
          borderLeft: isInterp ? `10px solid ${color.interp}` : undefined,
          paddingLeft: isInterp ? 40 : 0,
        }}
      >
      {lines.map((line, i) => {
        const p = spring({frame: frame - startAt - i * STAGGER, fps, config: {damping: 200}});
        const style: React.CSSProperties = {
          opacity: p,
          transform: `translateY(${interpolate(p, [0, 1], [40, 0])}px)`,
          wordBreak: 'keep-all',
        };
        if (line.kind === 'interp') {
          return (
            <div key={i} style={style}>
              <span
                style={{
                  display: 'inline-block',
                  background: color.interpSoft,
                  color: color.interp,
                  fontSize: size.chip,
                  fontWeight: 700,
                  padding: '10px 24px',
                  borderRadius: 999,
                }}
              >
                {line.text}
              </span>
            </div>
          );
        }
        if (line.kind === 'caution') {
          return (
            <div key={i} style={{...style, fontSize: size.chip, fontWeight: 500, color: color.caution}}>
              ※ {line.text}
            </div>
          );
        }
        if (line.kind === 'number') {
          return (
            <div key={i} style={style}>
              {line.before && <div style={{fontSize: size.line, fontWeight: 500, color: color.inkSoft}}>{line.before}</div>}
              <div style={{fontSize: size.number, fontWeight: 900, color: color.accent, lineHeight: 1.05, letterSpacing: -4}}>
                {line.number}
              </div>
              {line.after && <div style={{fontSize: size.line, fontWeight: 700}}>{line.after}</div>}
            </div>
          );
        }
        return (
          <div key={i} style={{...style, fontSize: i === 0 && !isInterp ? size.headline : size.line, fontWeight: i === 0 ? 900 : 700, lineHeight: 1.25}}>
            {line.text}
          </div>
        );
      })}
      </div>
    </div>
  );
};
