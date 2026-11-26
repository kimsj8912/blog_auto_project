import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, color, size} from '../theme';
import type {Word} from '../types';

/** 한 줄 최대 글자 수(공백 포함). 1080px 폭, 54px 글자 기준. */
export const MAX_LINE_CHARS = 16;

/** 단어를 자막 줄로 묶는다. 문장부호로 끝나는 단어에서 줄을 끊는다. */
export const groupWords = (words: Word[], maxChars = MAX_LINE_CHARS): Word[][] => {
  const lines: Word[][] = [];
  let cur: Word[] = [];
  let len = 0;
  for (const w of words) {
    const add = (cur.length ? 1 : 0) + w.text.length;
    if (cur.length && len + add > maxChars) {
      lines.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(w);
    len += (cur.length > 1 ? 1 : 0) + w.text.length;
    if (/[.?!,]$/.test(w.text)) {
      lines.push(cur);
      cur = [];
      len = 0;
    }
  }
  if (cur.length) lines.push(cur);
  return lines;
};

/** 지금 보여 줄 자막 줄. 말하기 전에는 없고, 줄 사이 쉼에서는 앞 줄을 유지한다. */
export const activeLine = (lines: Word[][], t: number): Word[] | null => {
  if (!lines.length || t < lines[0][0].start) return null;
  let found = lines[0];
  for (const line of lines) {
    if (line[0].start <= t) found = line;
  }
  return found;
};

export const Caption: React.FC<{words: Word[]; speechStart: number}> = ({words, speechStart}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps - speechStart;
  const line = activeLine(groupWords(words), t);
  if (!line) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: size.gutter,
        right: size.gutter,
        bottom: 300,
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          background: color.captionBg,
          borderRadius: 20,
          padding: '18px 30px',
          fontFamily: FONT,
          fontSize: size.caption,
          fontWeight: 700,
          lineHeight: 1.3,
          color: color.captionInk,
          textAlign: 'center',
          wordBreak: 'keep-all',
        }}
      >
        {line.map((w, i) => (
          <span key={i} style={{color: w.start <= t ? color.captionActive : color.captionInk}}>
            {i ? ' ' : ''}
            {w.text}
          </span>
        ))}
      </div>
    </div>
  );
};
