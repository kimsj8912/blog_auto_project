import React from 'react';
import {Audio, Sequence, staticFile, useVideoConfig} from 'remotion';

/** 장면 음성. 장면 시작에서 speechStart초 뒤에 말이 시작된다. */
export const Narration: React.FC<{file: string; speechStart: number}> = ({file, speechStart}) => {
  const {fps} = useVideoConfig();
  return (
    <Sequence from={Math.round(speechStart * fps)} layout="none" name={`음성 ${file}`}>
      <Audio src={staticFile(file)} />
    </Sequence>
  );
};
