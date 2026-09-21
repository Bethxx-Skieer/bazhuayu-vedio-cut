import React from 'react';
import {Composition} from 'remotion';
import {KnowledgeExplainer} from './KnowledgeExplainer';
import {project} from './project.generated';

export const RemotionRoot: React.FC = () => {
  const durationSec = Math.max(
    1,
    ...project.scenes.map((scene) => scene.startSec + scene.durationSec),
    project.voiceover.durationSec ?? 0,
  );
  return (
    <Composition
      id="KnowledgeExplainer"
      component={KnowledgeExplainer}
      durationInFrames={Math.ceil(durationSec * project.format.fps)}
      fps={project.format.fps}
      width={project.format.width}
      height={project.format.height}
    />
  );
};
