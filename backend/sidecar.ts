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
import type { AMABackend } from "./base.ts";
import { SidecarAPIError } from "./base.ts";

export class SidecarBackend implements AMABackend {
  private readonly baseUrl: string;

  constructor(port: number) {
    this.baseUrl = `http://127.0.0.1:${port}`;
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(30_000),
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const json = (await response.json()) as Record<string, unknown>;
        detail =
          typeof json.detail === "string"
            ? json.detail
            : JSON.stringify(json);
      } catch {
        // ignore parse failure
      }
      throw new SidecarAPIError(response.status, path, detail);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return (await response.json()) as T;
  }

  async init(params: InitParams): Promise<void> {
    await this.request("POST", "/init", params);
  }

  async forwardUser(params: ForwardUserParams): Promise<ForwardResult> {
    return this.request<ForwardResult>("POST", "/forward-user", params);
  }

  async forwardRobot(
    params: ForwardRobotParams,
  ): Promise<ForwardRobotResult> {
    return this.request<ForwardRobotResult>("POST", "/forward-robot", params);
  }

  async forwardRetrieve(params: RetrieveParams): Promise<RetrieveResult> {
    return this.request<RetrieveResult>("POST", "/forward-retrieve", params);
  }

  async judgeAndGenerate(user: string): Promise<void> {
    await this.request("POST", "/judge-and-generate", { user });
  }

  async clearAllMemory(user: string): Promise<void> {
    await this.request("POST", "/clear-all-memory", { user });
  }

  async health(): Promise<boolean> {
    const result = await this.request<{ status?: string }>(
      "GET",
      "/health",
    );
    return result.status === "ok";
  }

  async stats(user: string): Promise<StatsResult> {
    return this.request<StatsResult>("GET", `/stats/${encodeURIComponent(user)}`);
  }
}

