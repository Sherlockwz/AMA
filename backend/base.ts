import type {
  ForwardResult,
  ForwardRobotParams,
  ForwardRobotResult,
  ForwardUserParams,
  InitParams,
  RetrieveParams,
  RetrieveResult,
  StatsResult,
} from "../types.ts";

export interface AMABackend {
  init(params: InitParams): Promise<void>;
  forwardUser(params: ForwardUserParams): Promise<ForwardResult>;
  forwardRobot(params: ForwardRobotParams): Promise<ForwardRobotResult>;
  forwardRetrieve(params: RetrieveParams): Promise<RetrieveResult>;
  judgeAndGenerate(user: string): Promise<void>;
  clearAllMemory(user: string): Promise<void>;
  health(): Promise<boolean>;
  stats(user: string): Promise<StatsResult>;
}

export class SidecarAPIError extends Error {
  constructor(
    public status: number,
    public path: string,
    message: string,
  ) {
    super(`AMA sidecar error ${status} at ${path}: ${message}`);
    this.name = "SidecarAPIError";
  }
}

