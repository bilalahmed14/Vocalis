"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

type Schema = {
  type?: string | string[];
  title?: string;
  description?: string;
  default?: unknown;
  enum?: unknown[];
  examples?: unknown[];
  items?: Schema;
  minimum?: number;
  maximum?: number;
};

type Params = Record<string, unknown>;

/**
 * Renders a form from a provider's params JSON Schema, so a new provider needs no
 * dashboard change to become editable.
 */
export function ParamsForm({
  schema,
  values,
  required = [],
  onChange,
}: {
  schema: Record<string, Schema>;
  values: Params;
  required?: string[];
  onChange: (params: Params) => void;
}) {
  const set = (name: string, value: unknown) => {
    const next = { ...values };
    if (value === undefined || value === "") delete next[name];
    else next[name] = value;
    onChange(next);
  };

  return (
    <div className="space-y-3">
      {Object.entries(schema).map(([name, field]) => (
        <div key={name} className="space-y-1">
          <Label htmlFor={name} className="text-xs">
            {field.title ?? name}
            {required.includes(name) ? <span className="text-destructive"> *</span> : null}
          </Label>
          <Field name={name} field={field} value={values[name]} onChange={(value) => set(name, value)} />
          {field.description ? (
            <p className="text-[11px] leading-snug text-muted-foreground">{field.description}</p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function Field({
  name,
  field,
  value,
  onChange,
}: {
  name: string;
  field: Schema;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const placeholder = String(field.default ?? field.examples?.[0] ?? "");

  if (field.enum) {
    return (
      <select
        id={name}
        value={value === undefined ? "" : String(value)}
        onChange={(event) => onChange(event.target.value || undefined)}
        className="h-8 w-full rounded-md border bg-transparent px-2 text-sm"
      >
        <option value="">{placeholder ? `${placeholder} (default)` : "default"}</option>
        {field.enum.map((option) => (
          <option key={String(option)} value={String(option)}>
            {String(option)}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "boolean") {
    return (
      <div className="flex h-8 items-center">
        <Switch id={name} checked={Boolean(value ?? field.default)} onCheckedChange={onChange} />
      </div>
    );
  }

  if (field.type === "number" || field.type === "integer") {
    return (
      <Input
        id={name}
        type="number"
        className="h-8"
        min={field.minimum}
        max={field.maximum}
        step={field.type === "integer" ? 1 : "any"}
        placeholder={placeholder}
        value={value === undefined ? "" : String(value)}
        onChange={(event) =>
          onChange(event.target.value === "" ? undefined : Number(event.target.value))
        }
      />
    );
  }

  if (field.type === "array") {
    const list = Array.isArray(value) ? (value as unknown[]) : [];
    return (
      <Input
        id={name}
        className="h-8"
        placeholder="comma separated"
        value={list.join(", ")}
        onChange={(event) => {
          const items = event.target.value
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
          onChange(items.length ? items : undefined);
        }}
      />
    );
  }

  return (
    <Input
      id={name}
      className="h-8"
      placeholder={placeholder}
      value={value === undefined ? "" : String(value)}
      onChange={(event) => onChange(event.target.value || undefined)}
    />
  );
}
