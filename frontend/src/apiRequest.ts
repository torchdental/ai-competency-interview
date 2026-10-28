// FastAPI sends `detail` as a string, as {validation_errors} from claim validation,
// or as a list of field errors when the request itself is malformed.
interface ErrorBody {
  detail?:
    | string
    | { validation_errors?: string[] }
    | { loc: (string | number)[]; msg: string }[];
}

export async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(await errorMessage(res));
  return res.json() as Promise<T>;
}

async function errorMessage(res: Response): Promise<string> {
  const fallback = `Request failed with status ${res.status}`;
  let body: ErrorBody;
  try {
    body = await res.json();
  } catch {
    return fallback;
  }

  const detail = body.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => {
        // Drop the leading "body"/"query"/"path" segment from the field location.
        const field = e.loc.slice(1).join(".");
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join("; ");
  }
  if (detail?.validation_errors?.length) return detail.validation_errors.join("; ");
  return fallback;
}
