import type React from 'react';
import type {SceneProps} from '../types';
import {DefaultScene} from './DefaultScene';

/**
 * 장면 번호 → 장면 컴포넌트. 등록하지 않은 장면은 DefaultScene으로 그린다.
 * 원문마다 따로 연출한 장면 파일은 이 폴더에 두고 여기 등록한다.
 * 장면 파일은 theme.ts의 토큰과 components/의 공통 부품만 쓰고, 자막·음성·시간은 건드리지 않는다.
 */
export const CUSTOM_SCENES: Record<number, React.FC<SceneProps>> = {};

export const sceneComponent = (index: number): React.FC<SceneProps> => CUSTOM_SCENES[index] ?? DefaultScene;
