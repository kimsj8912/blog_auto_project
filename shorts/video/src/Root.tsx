import React from 'react';
import {AbsoluteFill, CalculateMetadataFunction, Composition, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {Caption} from './components/Caption';
import {Frame} from './components/Frame';
import {Narration} from './components/Narration';
import {loadRun, sceneFrames, totalFrames} from './data';
import {sceneComponent} from './scenes/registry';
import {FPS, HEIGHT, WIDTH} from './theme';
import type {RunData} from './types';

type Props = {run: RunData | null};

const Shorts: React.FC<Props> = ({run}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  if (!run) return null;
  return (
    <AbsoluteFill>
      {sceneFrames(run, fps).map(({scene, from, durationInFrames: d}) => {
        const Comp = sceneComponent(scene.index);
        return (
          <Sequence key={scene.index} from={from} durationInFrames={d} name={`장면 ${scene.index} ${scene.purpose}`}>
            <Frame progress={frame / durationInFrames} origin={run.origin}>
              <Comp scene={scene} fps={fps} durationInFrames={d} />
              <Caption words={scene.words} speechStart={scene.speechStart} />
            </Frame>
            <Narration file={scene.audio} speechStart={scene.speechStart} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

// 장면 길이는 음성 길이로 정해지므로, 렌더 전에 실행 폴더를 읽어 전체 길이를 계산한다.
const calculateMetadata: CalculateMetadataFunction<Props> = async () => {
  const run = await loadRun();
  return {durationInFrames: totalFrames(run, FPS), props: {run}};
};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Shorts"
    component={Shorts}
    width={WIDTH}
    height={HEIGHT}
    fps={FPS}
    durationInFrames={FPS}
    defaultProps={{run: null}}
    calculateMetadata={calculateMetadata}
  />
);
