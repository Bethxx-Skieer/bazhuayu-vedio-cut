import type React from 'react';
import type {Scene} from './types';

export type CustomSceneRenderer = React.FC<{scene: Scene; localFrame: number}>;
export type CustomTransitionRenderer = React.FC<{from: Scene; to: Scene; progress: number}>;

// Register a purpose-built scene or transition by sceneId when a knowledge
// relationship requires more than the basic image-and-label scaffold.
// The custom scene owns its visible objects; the scaffold will not duplicate them.
export const customScenes: Record<string, CustomSceneRenderer> = {};
export const customTransitions: Record<string, CustomTransitionRenderer> = {};
