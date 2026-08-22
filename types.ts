export interface AMAConfig {
  llmApiKey: string;
  llmBaseUrl: string;
  embeddingApiUrl: string;
  userId: string;
  modelMemory: string;
  temperature: number;
  memoryWindowSize: number;
  memoryWindowLength: number;
  turnRetrieve: number;
  topK: number;
  dataDir: string;
  pythonExecutable: string;
  autoCapture: boolean;
  autoRecall: boolean;
  sidecarPort: number;
  sidecarAutoStart: boolean;
  needsSetup: boolean;
}

export interface MemoryRecord extends Record<string, unknown> {
  content?: string;
}

export interface MultiGranularityRetrieval {
  text_match_results?: MemoryRecord[];
  fact_match_results?: MemoryRecord[];
  episodes_results?: MemoryRecord[];
}

export type RetrievalPayload = MemoryRecord[] | MultiGranularityRetrieval;
export type MemoryWindow = Array<Record<string, unknown>>;

export interface InitParams {
  user: string;
  dataDir: string;
  modelMemory: string;
  temperature: number;
  memoryWindowSize: number;
  memoryWindowLength: number;
  turnRetrieve: number;
}

export interface ForwardUserParams {
  user: string;
  userInput: string | Record<string, unknown>;
  showUsage?: boolean;
}

export interface ForwardRobotParams {
  user: string;
  robotOutput: string;
  showUsage?: boolean;
  timeInput?: string;
}

export interface RetrieveParams {
  user: string;
  userInput: string;
  showUsage?: boolean;
  strongRetrieve?: boolean;
}

export interface ForwardResult {
  retrievals: RetrievalPayload;
  memoryWindow: MemoryWindow;
}

export interface ForwardRobotResult {
  constructDecision?: unknown;
  memoryWindow: MemoryWindow;
}

export type RetrieveResult = ForwardResult;

export interface StatsResult {
  user: string;
  memoryWindowSize: number;
  records: {
    dialogues: number;
    facts: number;
    episodes: number;
    sentences: number;
  };
}
