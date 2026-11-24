import type { ReactNode } from 'react'

/** Visual workspace wrapper. The referenced Prompt Bond source asset was not included with the supplied project files. */
export function PromptBondScene({ children }: { children: ReactNode }) {
  return <div className="scene"><div className="scene-orbit orbit-one"/><div className="scene-orbit orbit-two"/><div className="scene-grain" aria-hidden="true"/>{children}</div>
}
