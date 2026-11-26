import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FONT, color, size} from '../theme';

/** 모든 장면 공통 바탕: 배경, 위쪽 진행 막대, 아래쪽 출처. */
export const Frame: React.FC<{
  progress: number;
  origin: string;
  children?: React.ReactNode;
}> = ({progress, origin, children}) => (
  <AbsoluteFill style={{background: color.bg, fontFamily: FONT, color: color.ink}}>
    <div style={{position: 'absolute', top: 0, left: 0, height: 10, width: `${progress * 100}%`, background: color.accent}} />
    {children}
    <div
      style={{
        position: 'absolute',
        left: size.gutter,
        right: size.gutter,
        bottom: 120,
        fontSize: size.footer,
        color: color.inkSoft,
        textAlign: 'center',
        overflow: 'hidden',
        whiteSpace: 'nowrap',
        textOverflow: 'ellipsis',
      }}
    >
      출처: {origin.replace(/^https?:\/\//, '')}
    </div>
  </AbsoluteFill>
);
