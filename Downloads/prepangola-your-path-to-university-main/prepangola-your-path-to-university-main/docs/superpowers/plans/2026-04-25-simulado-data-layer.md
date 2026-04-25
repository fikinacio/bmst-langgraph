# Simulado Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mock data in Simulado/Resultado/Revisao pages with live Supabase calls, implementing the full simulado lifecycle (create → answer → finish).

**Architecture:** Pure client-side SPA (Vite + React Router). All backend interaction uses the Supabase anon key client — no API routes. Data functions live in `src/lib/data/`. Types are manually maintained in `src/lib/supabase/types.ts` (sourced from CLAUDE.md schema). The URL param `:id` in `/simulado/:id` is the `attemptId`.

**Tech Stack:** Vite 5, React 18, TypeScript 5, React Router 6, @supabase/supabase-js 2, Bun

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `src/lib/supabase/types.ts` | Add `questions`, `exam_questions`, `attempt_answers`, `progress_snapshots` table types |
| Create | `src/lib/data/questions.ts` | `getRandomQuestions`, `getExamById`, `getQuestionById` |
| Create | `src/lib/data/simulado.ts` | `createSimulado`, `submitAnswer`, `finishSimulado` |
| Create | `src/pages/Simulados.tsx` | Subject/level selector that calls `createSimulado` and navigates to player |
| Modify | `src/App.tsx` | Add `/simulados` route |
| Rewrite | `src/pages/Simulado.tsx` | Load real exam+questions, track answers, batch-save on finish |
| Rewrite | `src/pages/Resultado.tsx` | Load real attempt result from Supabase |
| Rewrite | `src/pages/Revisao.tsx` | Load real questions + user answers |
| Modify | `src/pages/Dashboard.tsx` | Fix "Continuar" link: use `attempt.id` (not `examId`) |

---

## DB prerequisite (run in Supabase SQL editor before testing)

```sql
-- Unique constraint needed for answer upsert
ALTER TABLE attempt_answers
  ADD CONSTRAINT uq_attempt_question UNIQUE (attempt_id, question_id);

-- Unique constraint needed for progress snapshot upsert  
ALTER TABLE progress_snapshots
  ADD CONSTRAINT uq_user_subject_date UNIQUE (user_id, subject_id, snapshot_date);
```

---

## Task 1: Extend Supabase types

**Files:**
- Modify: `src/lib/supabase/types.ts`

- [ ] **Step 1: Open `src/lib/supabase/types.ts` and replace the `Tables` block** with the version below. Keep the `profiles`, `subjects`, `exams`, `attempts` tables exactly as they are; add the four new ones inside the same `Tables` object.

```typescript
// Regenerar via Supabase CLI assim que o projecto estiver ligado:
// npx supabase gen types typescript --project-id <project-id> > src/lib/supabase/types.ts

export type Database = {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string;
          full_name: string;
          role: 'student' | 'teacher' | 'admin';
          plan: 'free' | 'student' | 'family' | 'school';
          school_name: string | null;
          phone: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id: string;
          full_name: string;
          role?: 'student' | 'teacher' | 'admin';
          plan?: 'free' | 'student' | 'family' | 'school';
          school_name?: string | null;
          phone?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          full_name?: string;
          role?: 'student' | 'teacher' | 'admin';
          plan?: 'free' | 'student' | 'family' | 'school';
          school_name?: string | null;
          phone?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      subjects: {
        Row: {
          id: string;
          name: string;
          code: string;
          icon: string | null;
          active: boolean;
        };
        Insert: {
          id?: string;
          name: string;
          code: string;
          icon?: string | null;
          active?: boolean;
        };
        Update: {
          id?: string;
          name?: string;
          code?: string;
          icon?: string | null;
          active?: boolean;
        };
      };
      exams: {
        Row: {
          id: string;
          title: string;
          subject_id: string | null;
          level: string | null;
          question_count: number;
          time_limit_minutes: number;
          class_id: string | null;
          created_by: string | null;
          is_public: boolean;
          created_at: string;
        };
        Insert: {
          id?: string;
          title: string;
          subject_id?: string | null;
          level?: string | null;
          question_count?: number;
          time_limit_minutes?: number;
          class_id?: string | null;
          created_by?: string | null;
          is_public?: boolean;
          created_at?: string;
        };
        Update: {
          id?: string;
          title?: string;
          subject_id?: string | null;
          level?: string | null;
          question_count?: number;
          time_limit_minutes?: number;
          class_id?: string | null;
          created_by?: string | null;
          is_public?: boolean;
          created_at?: string;
        };
      };
      attempts: {
        Row: {
          id: string;
          user_id: string;
          exam_id: string;
          started_at: string;
          finished_at: string | null;
          score: number | null;
          total_questions: number | null;
          status: 'in_progress' | 'completed' | 'abandoned';
        };
        Insert: {
          id?: string;
          user_id: string;
          exam_id: string;
          started_at?: string;
          finished_at?: string | null;
          score?: number | null;
          total_questions?: number | null;
          status?: 'in_progress' | 'completed' | 'abandoned';
        };
        Update: {
          id?: string;
          user_id?: string;
          exam_id?: string;
          started_at?: string;
          finished_at?: string | null;
          score?: number | null;
          total_questions?: number | null;
          status?: 'in_progress' | 'completed' | 'abandoned';
        };
      };
      questions: {
        Row: {
          id: string;
          subject_id: string;
          level: '10' | '11' | '12' | 'acesso';
          difficulty: 'easy' | 'medium' | 'hard';
          statement: string;
          option_a: string;
          option_b: string;
          option_c: string;
          option_d: string;
          correct_option: 'a' | 'b' | 'c' | 'd';
          explanation: string | null;
          image_url: string | null;
          submitted_by: string | null;
          status: 'pending' | 'approved' | 'rejected';
          created_at: string;
        };
        Insert: {
          id?: string;
          subject_id: string;
          level: '10' | '11' | '12' | 'acesso';
          difficulty?: 'easy' | 'medium' | 'hard';
          statement: string;
          option_a: string;
          option_b: string;
          option_c: string;
          option_d: string;
          correct_option: 'a' | 'b' | 'c' | 'd';
          explanation?: string | null;
          image_url?: string | null;
          submitted_by?: string | null;
          status?: 'pending' | 'approved' | 'rejected';
          created_at?: string;
        };
        Update: {
          id?: string;
          subject_id?: string;
          level?: '10' | '11' | '12' | 'acesso';
          difficulty?: 'easy' | 'medium' | 'hard';
          statement?: string;
          option_a?: string;
          option_b?: string;
          option_c?: string;
          option_d?: string;
          correct_option?: 'a' | 'b' | 'c' | 'd';
          explanation?: string | null;
          image_url?: string | null;
          submitted_by?: string | null;
          status?: 'pending' | 'approved' | 'rejected';
          created_at?: string;
        };
      };
      exam_questions: {
        Row: {
          exam_id: string;
          question_id: string;
          position: number;
        };
        Insert: {
          exam_id: string;
          question_id: string;
          position: number;
        };
        Update: {
          exam_id?: string;
          question_id?: string;
          position?: number;
        };
      };
      attempt_answers: {
        Row: {
          id: string;
          attempt_id: string;
          question_id: string;
          selected_option: 'a' | 'b' | 'c' | 'd' | null;
          is_correct: boolean | null;
          answered_at: string;
        };
        Insert: {
          id?: string;
          attempt_id: string;
          question_id: string;
          selected_option?: 'a' | 'b' | 'c' | 'd' | null;
          is_correct?: boolean | null;
          answered_at?: string;
        };
        Update: {
          id?: string;
          attempt_id?: string;
          question_id?: string;
          selected_option?: 'a' | 'b' | 'c' | 'd' | null;
          is_correct?: boolean | null;
          answered_at?: string;
        };
      };
      progress_snapshots: {
        Row: {
          id: string;
          user_id: string;
          subject_id: string;
          accuracy_pct: number | null;
          attempts_count: number | null;
          snapshot_date: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          subject_id: string;
          accuracy_pct?: number | null;
          attempts_count?: number | null;
          snapshot_date?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          subject_id?: string;
          accuracy_pct?: number | null;
          attempts_count?: number | null;
          snapshot_date?: string;
        };
      };
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
  };
};
```

- [ ] **Step 2: Verify types compile**

```bash
cd prepangola-your-path-to-university-main && bunx tsc --noEmit
```
Expected: no errors from `types.ts`.

- [ ] **Step 3: Commit**

```bash
git add src/lib/supabase/types.ts
git commit -m "feat: extend supabase types with questions, exam_questions, attempt_answers, progress_snapshots"
```

---

## Task 2: Create questions data layer

**Files:**
- Create: `src/lib/data/questions.ts`

- [ ] **Step 1: Create the file**

```typescript
// src/lib/data/questions.ts
import { supabase } from "@/lib/supabase/client";
import type { Database } from "@/lib/supabase/types";

type QuestionRow = Database["public"]["Tables"]["questions"]["Row"];
type SubjectRow = Database["public"]["Tables"]["subjects"]["Row"];

export type Question = QuestionRow & {
  subjects: Pick<SubjectRow, "name" | "icon"> | null;
};

export type ExamWithQuestions = Database["public"]["Tables"]["exams"]["Row"] & {
  questions: Question[];
};

type EQJoinRow = {
  position: number;
  questions: Question | null;
};

/** Returns up to `count` random approved questions for a subject+level. */
export async function getRandomQuestions(
  subjectId: string,
  level: string,
  count: number,
  excludeIds: string[] = [],
): Promise<Question[]> {
  let query = supabase
    .from("questions")
    .select("*, subjects(name, icon)")
    .eq("subject_id", subjectId)
    .eq("level", level)
    .eq("status", "approved")
    .limit(count * 4); // over-fetch then shuffle

  if (excludeIds.length > 0) {
    query = query.not("id", "in", `(${excludeIds.join(",")})`);
  }

  const { data, error } = await query;
  if (error) throw error;
  if (!data?.length) return [];

  const shuffled = [...data].sort(() => Math.random() - 0.5);
  return (shuffled.slice(0, count)) as Question[];
}

/** Returns exam row plus its questions in position order. */
export async function getExamById(examId: string): Promise<ExamWithQuestions | null> {
  const { data: exam, error: examErr } = await supabase
    .from("exams")
    .select("*")
    .eq("id", examId)
    .single();
  if (examErr || !exam) return null;

  const { data: eqRows, error: eqErr } = await supabase
    .from("exam_questions")
    .select("position, questions(*, subjects(name, icon))")
    .eq("exam_id", examId)
    .order("position");
  if (eqErr) throw eqErr;

  const questions = ((eqRows ?? []) as unknown as EQJoinRow[])
    .map((r) => r.questions)
    .filter((q): q is Question => q !== null);

  return { ...exam, questions };
}

/** Returns a single question with subject info, or null. */
export async function getQuestionById(questionId: string): Promise<Question | null> {
  const { data, error } = await supabase
    .from("questions")
    .select("*, subjects(name, icon)")
    .eq("id", questionId)
    .single();
  if (error) return null;
  return data as Question;
}
```

- [ ] **Step 2: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/data/questions.ts
git commit -m "feat: add questions data layer (getRandomQuestions, getExamById, getQuestionById)"
```

---

## Task 3: Create simulado data layer

**Files:**
- Create: `src/lib/data/simulado.ts`

- [ ] **Step 1: Create the file**

```typescript
// src/lib/data/simulado.ts
import { supabase } from "@/lib/supabase/client";
import { getRandomQuestions } from "./questions";

export interface CreateSimuladoOptions {
  subjectId: string;
  level: string;
  questionCount: number;
  classExamId?: string;
}

export interface CreateSimuladoResult {
  attemptId: string;
  examId: string;
}

export async function createSimulado(
  opts: CreateSimuladoOptions,
): Promise<CreateSimuladoResult> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Utilizador não autenticado");

  // Enforce free-plan monthly limit (10 simulados/month)
  const { data: profile } = await supabase
    .from("profiles")
    .select("plan")
    .eq("id", user.id)
    .single();

  if (profile?.plan === "free") {
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    const { count } = await supabase
      .from("attempts")
      .select("*", { count: "exact", head: true })
      .eq("user_id", user.id)
      .gte("started_at", monthStart.toISOString());

    if ((count ?? 0) >= 10) {
      throw new Error(
        "Limite de 10 simulados mensais atingido. Actualiza o teu plano para continuar.",
      );
    }
  }

  const questions = await getRandomQuestions(
    opts.subjectId,
    opts.level,
    opts.questionCount,
  );

  if (questions.length < opts.questionCount) {
    throw new Error(
      `Banco de questões insuficiente para este filtro (encontradas: ${questions.length}, necessárias: ${opts.questionCount}).`,
    );
  }

  // Resolve subject name for the exam title
  const { data: subject } = await supabase
    .from("subjects")
    .select("name")
    .eq("id", opts.subjectId)
    .single();

  const levelLabel =
    opts.level === "acesso" ? "Acesso" : `${opts.level}.ª Classe`;
  const title = `${subject?.name ?? "Simulado"} — ${levelLabel}`;

  // Create exam record
  const { data: exam, error: examErr } = await supabase
    .from("exams")
    .insert({
      title,
      subject_id: opts.subjectId,
      level: opts.level,
      question_count: opts.questionCount,
      time_limit_minutes: opts.questionCount * 2, // 2 min per question
      class_id: opts.classExamId ?? null,
      created_by: user.id,
      is_public: false,
    })
    .select()
    .single();

  if (examErr || !exam) throw examErr ?? new Error("Falha ao criar exame");

  // Link questions to exam
  const { error: eqErr } = await supabase.from("exam_questions").insert(
    questions.map((q, i) => ({
      exam_id: exam.id,
      question_id: q.id,
      position: i + 1,
    })),
  );
  if (eqErr) throw eqErr;

  // Create attempt record
  const { data: attempt, error: attemptErr } = await supabase
    .from("attempts")
    .insert({
      user_id: user.id,
      exam_id: exam.id,
      total_questions: opts.questionCount,
      status: "in_progress",
    })
    .select()
    .single();

  if (attemptErr || !attempt)
    throw attemptErr ?? new Error("Falha ao criar tentativa");

  return { attemptId: attempt.id, examId: exam.id };
}

export interface SubmitAnswerOptions {
  attemptId: string;
  questionId: string;
  selectedOption: "a" | "b" | "c" | "d";
}

export interface SubmitAnswerResult {
  isCorrect: boolean;
  correctOption: "a" | "b" | "c" | "d";
}

export async function submitAnswer(
  opts: SubmitAnswerOptions,
): Promise<SubmitAnswerResult> {
  const { data: question, error: qErr } = await supabase
    .from("questions")
    .select("correct_option")
    .eq("id", opts.questionId)
    .single();

  if (qErr || !question) throw qErr ?? new Error("Questão não encontrada");

  const correctOption = question.correct_option as "a" | "b" | "c" | "d";
  const isCorrect = opts.selectedOption === correctOption;

  // Upsert — requires uq_attempt_question constraint on the table
  const { error } = await supabase.from("attempt_answers").upsert(
    {
      attempt_id: opts.attemptId,
      question_id: opts.questionId,
      selected_option: opts.selectedOption,
      is_correct: isCorrect,
    },
    { onConflict: "attempt_id,question_id" },
  );
  if (error) throw error;

  return { isCorrect, correctOption };
}

export interface SubjectResult {
  subjectId: string;
  subjectName: string;
  icon: string;
  correct: number;
  total: number;
}

export interface FinishSimuladoResult {
  score: number;
  totalQuestions: number;
  accuracyBySubject: SubjectResult[];
}

type AnswerJoinRow = {
  is_correct: boolean | null;
  question_id: string;
  questions: {
    subject_id: string;
    subjects: { name: string; icon: string | null } | null;
  } | null;
};

export async function finishSimulado(
  attemptId: string,
): Promise<FinishSimuladoResult> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) throw new Error("Utilizador não autenticado");

  const { data: attempt } = await supabase
    .from("attempts")
    .select("total_questions")
    .eq("id", attemptId)
    .single();

  const { data: rawAnswers, error: answersErr } = await supabase
    .from("attempt_answers")
    .select("is_correct, question_id, questions(subject_id, subjects(name, icon))")
    .eq("attempt_id", attemptId);

  if (answersErr) throw answersErr;

  const answers = (rawAnswers ?? []) as unknown as AnswerJoinRow[];
  const totalQuestions = attempt?.total_questions ?? answers.length;
  const score = answers.filter((a) => a.is_correct === true).length;

  // Build per-subject stats
  const subjectMap = new Map<
    string,
    { name: string; icon: string; correct: number; total: number }
  >();

  for (const ans of answers) {
    const subjectId = ans.questions?.subject_id;
    if (!subjectId) continue;
    const name = ans.questions?.subjects?.name ?? "";
    const icon = ans.questions?.subjects?.icon ?? "📚";
    const existing = subjectMap.get(subjectId) ?? { name, icon, correct: 0, total: 0 };
    existing.total += 1;
    if (ans.is_correct) existing.correct += 1;
    subjectMap.set(subjectId, existing);
  }

  // Mark attempt as completed
  await supabase
    .from("attempts")
    .update({ status: "completed", score, finished_at: new Date().toISOString() })
    .eq("id", attemptId);

  // Upsert progress snapshot per subject (requires uq_user_subject_date constraint)
  const today = new Date().toISOString().split("T")[0];

  await Promise.all(
    Array.from(subjectMap.entries()).map(([subjectId, stats]) =>
      supabase.from("progress_snapshots").upsert(
        {
          user_id: user.id,
          subject_id: subjectId,
          accuracy_pct: stats.total > 0 ? Math.round((stats.correct / stats.total) * 100) : 0,
          attempts_count: 1,
          snapshot_date: today,
        },
        { onConflict: "user_id,subject_id,snapshot_date" },
      ),
    ),
  );

  return {
    score,
    totalQuestions,
    accuracyBySubject: Array.from(subjectMap.entries()).map(([id, s]) => ({
      subjectId: id,
      subjectName: s.name,
      icon: s.icon,
      correct: s.correct,
      total: s.total,
    })),
  };
}
```

- [ ] **Step 2: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/lib/data/simulado.ts
git commit -m "feat: add simulado data layer (createSimulado, submitAnswer, finishSimulado)"
```

---

## Task 4: Create Simulados selection page + add route

**Files:**
- Create: `src/pages/Simulados.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Create `src/pages/Simulados.tsx`**

```typescript
// src/pages/Simulados.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { DashboardLayout } from "@/components/DashboardLayout";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { supabase } from "@/lib/supabase/client";
import { createSimulado } from "@/lib/data/simulado";
import { toast } from "@/hooks/use-toast";
import { Play } from "lucide-react";
import type { Database } from "@/lib/supabase/types";

type SubjectRow = Database["public"]["Tables"]["subjects"]["Row"];
type Level = "10" | "11" | "12" | "acesso";

const LEVELS: { value: Level; label: string }[] = [
  { value: "10", label: "10.ª Classe" },
  { value: "11", label: "11.ª Classe" },
  { value: "12", label: "12.ª Classe" },
  { value: "acesso", label: "Exame de Acesso" },
];

const COUNTS = [5, 10, 20];

export default function SimuladosPage() {
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<SubjectRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);

  const [subjectId, setSubjectId] = useState("");
  const [level, setLevel] = useState<Level>("12");
  const [questionCount, setQuestionCount] = useState(10);

  useEffect(() => {
    supabase
      .from("subjects")
      .select("*")
      .eq("active", true)
      .order("name")
      .then(({ data }) => {
        setSubjects(data ?? []);
        if (data?.length) setSubjectId(data[0].id);
        setLoading(false);
      });
  }, []);

  async function handleStart() {
    if (!subjectId || starting) return;
    setStarting(true);
    try {
      const { attemptId } = await createSimulado({ subjectId, level, questionCount });
      navigate(`/simulado/${attemptId}`);
    } catch (err) {
      toast({
        title: "Erro ao iniciar simulado",
        description: err instanceof Error ? err.message : "Tenta novamente.",
        variant: "destructive",
      });
      setStarting(false);
    }
  }

  return (
    <DashboardLayout type="student">
      <div className="max-w-xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-display font-bold mb-1">Novo Simulado</h1>
          <p className="text-muted-foreground text-sm">Escolhe a disciplina, classe e número de questões.</p>
        </div>

        <div className="rounded-xl border border-border bg-card p-6 space-y-6">
          {/* Subject */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Disciplina</label>
            {loading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {subjects.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => setSubjectId(s.id)}
                    className={`flex items-center gap-2 rounded-lg border-2 px-4 py-3 text-sm font-medium transition-all ${
                      subjectId === s.id
                        ? "border-primary bg-primary/5 text-primary"
                        : "border-border hover:border-primary/30"
                    }`}
                  >
                    <span>{s.icon ?? "📚"}</span>
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Level */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Classe</label>
            <div className="grid grid-cols-2 gap-2">
              {LEVELS.map((l) => (
                <button
                  key={l.value}
                  onClick={() => setLevel(l.value)}
                  className={`rounded-lg border-2 px-4 py-3 text-sm font-medium transition-all ${
                    level === l.value
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/30"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          {/* Question count */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Número de questões</label>
            <div className="flex gap-2">
              {COUNTS.map((n) => (
                <button
                  key={n}
                  onClick={() => setQuestionCount(n)}
                  className={`flex-1 rounded-lg border-2 py-3 text-sm font-bold transition-all ${
                    questionCount === n
                      ? "border-primary bg-primary/5 text-primary"
                      : "border-border hover:border-primary/30"
                  }`}
                >
                  {n}
                </button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              Tempo estimado: {questionCount * 2} minutos
            </p>
          </div>

          <Button
            variant="hero"
            size="lg"
            className="w-full"
            onClick={handleStart}
            disabled={!subjectId || starting || loading}
          >
            {starting ? "A preparar…" : <><Play size={18} /> Começar Simulado</>}
          </Button>
        </div>
      </div>
    </DashboardLayout>
  );
}
```

- [ ] **Step 2: Add `/simulados` route in `src/App.tsx`**

At the top of `src/App.tsx`, add the import after the existing page imports:

```typescript
import SimuladosPage from "./pages/Simulados";
```

Inside the `<Routes>` block, add after the `/progresso` route (line ~58):

```tsx
<Route path="/simulados" element={<ProtectedRoute><SimuladosPage /></ProtectedRoute>} />
```

- [ ] **Step 3: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/pages/Simulados.tsx src/App.tsx
git commit -m "feat: add simulados selection page and /simulados route"
```

---

## Task 5: Rewrite Simulado.tsx to use real data

**Files:**
- Rewrite: `src/pages/Simulado.tsx`

The `:id` URL param is the `attemptId`. The page loads the attempt → exam → questions from Supabase, shows the "antes" start screen with real exam info, then runs the exam. On finish it batch-submits all answers via `submitAnswer` then calls `finishSimulado`.

- [ ] **Step 1: Replace the full content of `src/pages/Simulado.tsx`**

```typescript
// src/pages/Simulado.tsx
import { useState, useEffect, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Clock, ArrowRight, ArrowLeft } from "lucide-react";
import { supabase } from "@/lib/supabase/client";
import { getExamById, type ExamWithQuestions } from "@/lib/data/questions";
import { submitAnswer, finishSimulado } from "@/lib/data/simulado";
import { toast } from "@/hooks/use-toast";

type PageState = "carregando" | "antes" | "decorrer" | "terminado";
type SelectedOption = "a" | "b" | "c" | "d";

const OPT_LABELS: SelectedOption[] = ["a", "b", "c", "d"];

export default function SimuladoPage() {
  const { id: attemptId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [pageState, setPageState] = useState<PageState>("carregando");
  const [exam, setExam] = useState<ExamWithQuestions | null>(null);
  const [currentQ, setCurrentQ] = useState(0);
  const [respostas, setRespostas] = useState<Record<string, SelectedOption>>({});
  const [timer, setTimer] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Load attempt → exam → questions
  useEffect(() => {
    if (!attemptId) return;

    supabase
      .from("attempts")
      .select("exam_id, status")
      .eq("id", attemptId)
      .single()
      .then(async ({ data: attempt, error }) => {
        if (error || !attempt) {
          navigate("/dashboard");
          return;
        }
        if (attempt.status === "completed") {
          navigate(`/simulado/${attemptId}/resultado`);
          return;
        }
        const examData = await getExamById(attempt.exam_id);
        if (!examData || !examData.questions.length) {
          toast({ title: "Simulado não encontrado", variant: "destructive" });
          navigate("/dashboard");
          return;
        }
        setExam(examData);
        setTimer(examData.time_limit_minutes * 60);
        setPageState("antes");
      });
  }, [attemptId, navigate]);

  // Countdown timer (only while in progress)
  useEffect(() => {
    if (pageState !== "decorrer") return;
    if (timer <= 0) {
      handleTerminar();
      return;
    }
    const interval = setInterval(() => setTimer((t) => t - 1), 1000);
    return () => clearInterval(interval);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageState, timer]);

  // Redirect when finished
  useEffect(() => {
    if (pageState === "terminado") {
      navigate(`/simulado/${attemptId}/resultado`);
    }
  }, [pageState, attemptId, navigate]);

  const handleTerminar = useCallback(async () => {
    if (!exam || !attemptId || submitting) return;
    setSubmitting(true);
    try {
      // Submit all collected answers to DB
      for (const [questionId, selectedOption] of Object.entries(respostas)) {
        await submitAnswer({ attemptId, questionId, selectedOption });
      }
      await finishSimulado(attemptId);
      setPageState("terminado");
    } catch (err) {
      toast({
        title: "Erro ao submeter simulado",
        description: err instanceof Error ? err.message : "Tenta novamente.",
        variant: "destructive",
      });
      setSubmitting(false);
    }
  }, [exam, attemptId, submitting, respostas]);

  // ── Loading ────────────────────────────────────────────────────────────────
  if (pageState === "carregando") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">A carregar simulado…</p>
      </div>
    );
  }

  // ── Before start ──────────────────────────────────────────────────────────
  if (pageState === "antes" && exam) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-background">
        <div className="max-w-md w-full text-center">
          <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 text-primary mx-auto mb-4">
              <Clock size={32} />
            </div>
            <h1 className="text-2xl font-display font-bold mb-2">{exam.title}</h1>
            <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground mb-6">
              <span>{exam.questions.length} questões</span>
              <span>•</span>
              <span>{exam.time_limit_minutes} minutos</span>
            </div>
            <Button
              variant="hero"
              size="lg"
              className="w-full"
              onClick={() => setPageState("decorrer")}
            >
              Começar Simulado
            </Button>
            <Button variant="ghost" className="w-full mt-2" asChild>
              <Link to="/dashboard">Voltar ao Dashboard</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // ── In progress ───────────────────────────────────────────────────────────
  if (!exam) return null;
  const questao = exam.questions[currentQ];
  const mins = Math.floor(timer / 60);
  const secs = timer % 60;
  const timerColor =
    mins < 5 ? (mins < 1 ? "text-destructive" : "text-accent") : "text-foreground";

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Questão {currentQ + 1} de {exam.questions.length}
          </span>
          <span className={cn("font-mono font-bold text-lg", timerColor)}>
            {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="text-destructive"
            onClick={handleTerminar}
            disabled={submitting}
          >
            {submitting ? "A guardar…" : "Terminar"}
          </Button>
        </div>
        {/* Progress bar */}
        <div className="max-w-3xl mx-auto mt-2">
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all duration-300"
              style={{ width: `${((currentQ + 1) / exam.questions.length) * 100}%` }}
            />
          </div>
        </div>
      </header>

      {/* Question */}
      <main className="flex-1 flex items-start justify-center p-4 md:p-8">
        <div className="max-w-2xl w-full">
          <div className="mb-8">
            <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded-full">
              {questao.subjects?.name ?? ""}
            </span>
            <h2 className="text-xl md:text-2xl font-semibold mt-4 leading-relaxed">
              {questao.statement}
            </h2>
          </div>

          <div className="space-y-3">
            {OPT_LABELS.map((opt) => {
              const text =
                opt === "a" ? questao.option_a
                : opt === "b" ? questao.option_b
                : opt === "c" ? questao.option_c
                : questao.option_d;
              const selected = respostas[questao.id] === opt;
              return (
                <button
                  key={opt}
                  onClick={() =>
                    setRespostas((prev) => ({ ...prev, [questao.id]: opt }))
                  }
                  className={cn(
                    "w-full text-left p-4 rounded-xl border-2 transition-all duration-200 flex items-center gap-3",
                    selected
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/30 hover:bg-muted/30",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold shrink-0 uppercase",
                      selected
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {opt}
                  </span>
                  <span className="text-sm md:text-base">{text}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center justify-between mt-8">
            <Button
              variant="ghost"
              onClick={() => setCurrentQ((q) => Math.max(0, q - 1))}
              disabled={currentQ === 0}
            >
              <ArrowLeft size={16} /> Anterior
            </Button>
            {currentQ < exam.questions.length - 1 ? (
              <Button
                variant="hero"
                onClick={() => setCurrentQ((q) => q + 1)}
                disabled={!respostas[questao.id]}
              >
                Próxima <ArrowRight size={16} />
              </Button>
            ) : (
              <Button
                variant="hero"
                onClick={handleTerminar}
                disabled={!respostas[questao.id] || submitting}
              >
                {submitting ? "A guardar…" : "Terminar Simulado"}
              </Button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/Simulado.tsx
git commit -m "feat: wire Simulado page to real Supabase data"
```

---

## Task 6: Rewrite Resultado.tsx to use real data

**Files:**
- Rewrite: `src/pages/Resultado.tsx`

- [ ] **Step 1: Replace the full content of `src/pages/Resultado.tsx`**

```typescript
// src/pages/Resultado.tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  CheckCircle2,
  XCircle,
  Clock,
  ArrowUp,
  ArrowDown,
  RotateCcw,
  Target,
  BookOpen,
} from "lucide-react";
import { supabase } from "@/lib/supabase/client";

interface SubjectStat {
  name: string;
  correct: number;
  total: number;
}

interface AttemptResult {
  title: string;
  score: number;
  totalQuestions: number;
  finishedAt: string;
  timeLimitMinutes: number;
  subjects: SubjectStat[];
  questionsCorrect: (boolean | null)[];
}

type AnswerJoin = {
  is_correct: boolean | null;
  question_id: string;
  questions: {
    subject_id: string;
    subjects: { name: string } | null;
  } | null;
};

async function loadResult(attemptId: string): Promise<AttemptResult | null> {
  const { data: attempt } = await supabase
    .from("attempts")
    .select("score, total_questions, finished_at, exam_id")
    .eq("id", attemptId)
    .single();
  if (!attempt) return null;

  const { data: rawExam } = await supabase
    .from("exams")
    .select("title, time_limit_minutes")
    .eq("id", attempt.exam_id)
    .single();

  const { data: rawAnswers } = await supabase
    .from("attempt_answers")
    .select("is_correct, question_id, questions(subject_id, subjects(name))")
    .eq("attempt_id", attemptId);

  const { data: examQuestions } = await supabase
    .from("exam_questions")
    .select("question_id, position")
    .eq("exam_id", attempt.exam_id)
    .order("position");

  const answers = (rawAnswers ?? []) as unknown as AnswerJoin[];
  const answerMap = new Map(answers.map((a) => [a.question_id, a.is_correct]));

  const questionsCorrect = (examQuestions ?? []).map(
    (eq) => answerMap.get(eq.question_id) ?? null,
  );

  // Subject breakdown
  const subjectMap = new Map<string, SubjectStat>();
  for (const ans of answers) {
    const subjectId = ans.questions?.subject_id;
    const name = ans.questions?.subjects?.name ?? "";
    if (!subjectId) continue;
    const s = subjectMap.get(subjectId) ?? { name, correct: 0, total: 0 };
    s.total += 1;
    if (ans.is_correct) s.correct += 1;
    subjectMap.set(subjectId, s);
  }

  return {
    title: (rawExam as { title: string } | null)?.title ?? "Simulado",
    score: attempt.score ?? 0,
    totalQuestions: attempt.total_questions ?? 0,
    finishedAt: attempt.finished_at ?? "",
    timeLimitMinutes: (rawExam as { time_limit_minutes: number } | null)?.time_limit_minutes ?? 40,
    subjects: Array.from(subjectMap.values()),
    questionsCorrect,
  };
}

function formatFinishedAt(iso: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("pt-AO", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function ResultadoPage() {
  const { id: attemptId } = useParams<{ id: string }>();
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [ringAnimated, setRingAnimated] = useState(false);

  useEffect(() => {
    if (!attemptId) return;
    loadResult(attemptId).then((r) => {
      setResult(r);
      setLoading(false);
      setTimeout(() => setRingAnimated(true), 100);
    });
  }, [attemptId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background py-8 px-4">
        <div className="max-w-2xl mx-auto space-y-6">
          <Skeleton className="h-36 w-36 rounded-full mx-auto" />
          <Skeleton className="h-8 w-48 mx-auto" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground">Resultado não encontrado.</p>
          <Button asChild><Link to="/dashboard">Voltar ao Dashboard</Link></Button>
        </div>
      </div>
    );
  }

  const { score, totalQuestions, title, finishedAt, subjects, questionsCorrect } = result;
  const percentage = totalQuestions > 0 ? Math.round((score / totalQuestions) * 100) : 0;
  const wrong = totalQuestions - score;
  const ringColor =
    percentage >= 70
      ? "hsl(var(--success))"
      : percentage >= 50
      ? "hsl(var(--accent))"
      : "hsl(var(--destructive))";
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (percentage / 100) * circumference;
  const label =
    percentage >= 70
      ? "Bom desempenho!"
      : percentage >= 50
      ? "Pode melhorar"
      : "Precisa de mais prática";

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="max-w-2xl mx-auto space-y-8 animate-fade-in">
        {/* Score Ring */}
        <div className="text-center">
          <div className="relative inline-block">
            <svg width="140" height="140" viewBox="0 0 120 120">
              <circle cx="60" cy="60" r="54" fill="none" stroke="hsl(var(--muted))" strokeWidth="8" />
              <circle
                cx="60" cy="60" r="54" fill="none"
                stroke={ringColor} strokeWidth="8" strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={ringAnimated ? offset : circumference}
                transform="rotate(-90 60 60)"
                style={{ transition: "stroke-dashoffset 1.2s ease-out" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-display font-bold">
                {score}<span className="text-muted-foreground text-lg">/{totalQuestions}</span>
              </span>
            </div>
          </div>
          <p className="text-2xl font-bold font-mono mt-2">{percentage}%</p>
          <p className="text-muted-foreground">{label}</p>
          <h1 className="text-lg font-semibold mt-3">{title}</h1>
          <p className="text-sm text-muted-foreground">{formatFinishedAt(finishedAt)}</p>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: CheckCircle2, label: "Respostas correctas", value: score, color: "text-success" },
            { icon: XCircle, label: "Respostas erradas", value: wrong, color: "text-destructive" },
            { icon: Clock, label: "Tempo limite", value: `${result.timeLimitMinutes} min`, color: "text-muted-foreground" },
          ].map((s) => (
            <div key={s.label} className="rounded-xl border border-border bg-card p-4 text-center">
              <s.icon className={cn("mx-auto mb-1", s.color)} size={20} />
              <p className={cn("text-2xl font-bold font-mono", s.color)}>{s.value}</p>
              <p className="text-xs text-muted-foreground">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Subject Breakdown */}
        {subjects.length > 0 && (
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h2 className="font-semibold">Desempenho por disciplina</h2>
            {subjects.map((s) => {
              const pct = s.total > 0 ? Math.round((s.correct / s.total) * 100) : 0;
              return (
                <div key={s.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{s.name}</span>
                    <span className="text-muted-foreground">{s.correct}/{s.total} — {pct}%</span>
                  </div>
                  <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className={cn("h-full rounded-full transition-all duration-700",
                        pct >= 70 ? "bg-success" : pct >= 50 ? "bg-accent" : "bg-destructive")}
                      style={{ width: ringAnimated ? `${pct}%` : "0%" }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Question Summary Strip */}
        {questionsCorrect.length > 0 && (
          <div className="rounded-xl border border-border bg-card p-5">
            <h2 className="font-semibold mb-3">Resumo por questão</h2>
            <div className="flex flex-wrap gap-1.5">
              {questionsCorrect.map((correct, i) => (
                <Link
                  key={i}
                  to={`/simulado/${attemptId}/revisao`}
                  className={cn(
                    "w-7 h-7 rounded text-[10px] font-bold flex items-center justify-center transition-transform hover:scale-125",
                    correct === true
                      ? "bg-success/20 text-success"
                      : correct === false
                      ? "bg-destructive/20 text-destructive"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {i + 1}
                </Link>
              ))}
            </div>
            <p className="text-xs text-muted-foreground mt-2">Clica numa questão para ver a explicação</p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="hero" className="flex-1" asChild>
            <Link to={`/simulado/${attemptId}/revisao`}>
              <BookOpen size={16} /> Rever respostas com explicações
            </Link>
          </Button>
          <Button variant="outline" className="flex-1" asChild>
            <Link to="/simulados">
              <RotateCcw size={16} /> Novo simulado
            </Link>
          </Button>
          <Button variant="ghost" className="flex-1" asChild>
            <Link to="/dashboard">
              <Target size={16} /> Dashboard
            </Link>
          </Button>
        </div>

        <p className="text-center text-sm text-muted-foreground pb-4">
          {percentage >= 70
            ? "Estás a evoluir! Continua assim."
            : "Não desistas. Cada tentativa é aprendizagem. Tenta de novo!"}
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add src/pages/Resultado.tsx
git commit -m "feat: wire Resultado page to real Supabase attempt data"
```

---

## Task 7: Rewrite Revisao.tsx to use real data + fix Dashboard link

**Files:**
- Rewrite: `src/pages/Revisao.tsx`
- Modify: `src/pages/Dashboard.tsx` (1-line fix)

- [ ] **Step 1: Replace the full content of `src/pages/Revisao.tsx`**

```typescript
// src/pages/Revisao.tsx
import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  XCircle,
  Lightbulb,
} from "lucide-react";
import { supabase } from "@/lib/supabase/client";
import type { Question } from "@/lib/data/questions";

interface ReviewQuestion extends Question {
  selectedOption: "a" | "b" | "c" | "d" | null;
  position: number;
}

type EQAnswerJoin = {
  position: number;
  question_id: string;
  questions: Question | null;
};

type AnswerRow = {
  question_id: string;
  selected_option: "a" | "b" | "c" | "d" | null;
};

async function loadReview(attemptId: string): Promise<ReviewQuestion[]> {
  const { data: attempt } = await supabase
    .from("attempts")
    .select("exam_id")
    .eq("id", attemptId)
    .single();
  if (!attempt) return [];

  const { data: rawEQ } = await supabase
    .from("exam_questions")
    .select("position, question_id, questions(*, subjects(name, icon))")
    .eq("exam_id", attempt.exam_id)
    .order("position");

  const { data: rawAnswers } = await supabase
    .from("attempt_answers")
    .select("question_id, selected_option")
    .eq("attempt_id", attemptId);

  const eqRows = (rawEQ ?? []) as unknown as EQAnswerJoin[];
  const answers = rawAnswers as AnswerRow[] | null;
  const answerMap = new Map(
    (answers ?? []).map((a) => [a.question_id, a.selected_option]),
  );

  return eqRows
    .filter((r) => r.questions !== null)
    .map((r) => ({
      ...(r.questions as Question),
      selectedOption: answerMap.get(r.question_id) ?? null,
      position: r.position,
    }));
}

export default function RevisaoPage() {
  const { id: attemptId } = useParams<{ id: string }>();
  const [questions, setQuestions] = useState<ReviewQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentQ, setCurrentQ] = useState(0);

  useEffect(() => {
    if (!attemptId) return;
    loadReview(attemptId).then((qs) => {
      setQuestions(qs);
      setLoading(false);
    });
  }, [attemptId]);

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <header className="sticky top-0 z-50 border-b border-border bg-card px-4 py-4">
          <Skeleton className="h-4 w-48 mx-auto" />
        </header>
        <main className="flex-1 flex items-start justify-center p-4 md:p-8">
          <div className="max-w-2xl w-full space-y-4">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-32 w-full" />
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}
          </div>
        </main>
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-muted-foreground">Sem questões para rever.</p>
          <Button asChild><Link to="/dashboard">Voltar ao Dashboard</Link></Button>
        </div>
      </div>
    );
  }

  const q = questions[currentQ];
  const acertou = q.selectedOption === q.correct_option;

  const optionText = (opt: "a" | "b" | "c" | "d") =>
    opt === "a" ? q.option_a
    : opt === "b" ? q.option_b
    : opt === "c" ? q.option_c
    : q.option_d;

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card px-4 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <Link
            to={`/simulado/${attemptId}/resultado`}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            ← Resultados
          </Link>
          <span className="text-sm font-medium">
            Questão {currentQ + 1} de {questions.length}
          </span>
        </div>
        <div className="max-w-3xl mx-auto mt-2">
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary transition-all"
              style={{ width: `${((currentQ + 1) / questions.length) * 100}%` }}
            />
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center p-4 md:p-8">
        <div className="max-w-2xl w-full">
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded-full">
                {q.subjects?.name ?? ""}
              </span>
              {q.selectedOption === null ? (
                <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded-full">
                  Não respondida
                </span>
              ) : acertou ? (
                <span className="flex items-center gap-1 text-xs text-success font-medium bg-success/10 px-2 py-1 rounded-full">
                  <CheckCircle2 size={12} /> Correcta
                </span>
              ) : (
                <span className="flex items-center gap-1 text-xs text-destructive font-medium bg-destructive/10 px-2 py-1 rounded-full">
                  <XCircle size={12} /> Incorrecta
                </span>
              )}
            </div>
            <h2 className="text-xl md:text-2xl font-semibold leading-relaxed">
              {q.statement}
            </h2>
          </div>

          <div className="space-y-3 mb-6">
            {(["a", "b", "c", "d"] as const).map((opt) => {
              const isCorrect = opt === q.correct_option;
              const isSelected = opt === q.selectedOption;
              const isWrong = isSelected && !isCorrect;
              return (
                <div
                  key={opt}
                  className={cn(
                    "w-full text-left p-4 rounded-xl border-2 flex items-center gap-3",
                    isCorrect && "border-success bg-success/5",
                    isWrong && "border-destructive bg-destructive/5",
                    !isCorrect && !isWrong && "border-border opacity-60",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold shrink-0",
                      isCorrect && "bg-success text-success-foreground",
                      isWrong && "bg-destructive text-destructive-foreground",
                      !isCorrect && !isWrong && "bg-muted text-muted-foreground",
                    )}
                  >
                    {isCorrect ? <CheckCircle2 size={16} /> : isWrong ? <XCircle size={16} /> : opt.toUpperCase()}
                  </span>
                  <span className="text-sm md:text-base">{optionText(opt)}</span>
                </div>
              );
            })}
          </div>

          {/* Explanation */}
          {q.explanation && (
            <div className="rounded-xl border border-accent/30 bg-accent/5 p-5">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb size={18} className="text-accent" />
                <h3 className="font-semibold text-sm">Explicação</h3>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">{q.explanation}</p>
            </div>
          )}

          <div className="flex items-center justify-between mt-8">
            <Button
              variant="ghost"
              onClick={() => setCurrentQ((q) => Math.max(0, q - 1))}
              disabled={currentQ === 0}
            >
              <ArrowLeft size={16} /> Anterior
            </Button>
            <Button
              variant="hero"
              onClick={() => setCurrentQ((q) => q + 1)}
              disabled={currentQ >= questions.length - 1}
            >
              Próxima <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
```

- [ ] **Step 2: Fix Dashboard "Continuar" link in `src/pages/Dashboard.tsx`**

Find line 146 in `src/pages/Dashboard.tsx`:
```tsx
<Link to={`/simulado/${data.inProgress.examId}`}>
```
Replace with:
```tsx
<Link to={`/simulado/${data.inProgress.id}`}>
```

- [ ] **Step 3: Verify types compile**

```bash
bunx tsc --noEmit
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add src/pages/Revisao.tsx src/pages/Dashboard.tsx
git commit -m "feat: wire Revisao page to real data; fix Dashboard continue link to use attemptId"
```

---

## Task 8: End-to-end smoke test

- [ ] **Step 1: Start the dev server**

```bash
cd prepangola-your-path-to-university-main && bun run dev
```
Open `http://localhost:5173`.

- [ ] **Step 2: Seed at least 3 approved questions in Supabase** (SQL editor)

```sql
-- First: ensure a subject exists
INSERT INTO subjects (name, code, icon, active)
VALUES ('Matemática', 'MAT', '📐', true)
ON CONFLICT (code) DO NOTHING;

-- Then: insert 3 questions
INSERT INTO questions (subject_id, level, statement, option_a, option_b, option_c, option_d, correct_option, status)
SELECT 
  s.id, '12', 
  'Questão de teste ' || g || ': Quanto é 2 + 2?',
  '4', '3', '5', '6', 'a', 'approved'
FROM subjects s, generate_series(1,3) g
WHERE s.code = 'MAT';
```

- [ ] **Step 3: Test the full flow**

1. Log in → go to `/simulados`
2. Select Matemática → 12.ª Classe → 3 questões → Começar
3. Verify redirect to `/simulado/:attemptId` and exam info screen appears
4. Click "Começar Simulado" → answer 3 questions → "Terminar Simulado"
5. Verify redirect to `/simulado/:attemptId/resultado` with real score
6. Click "Rever respostas" → verify questions appear with correct/wrong highlighting
7. Return to dashboard → verify attempt appears in "Actividade recente"
8. Verify "Continuar" banner appears if there's an in-progress attempt

- [ ] **Step 4: Verify free plan limit**

In Supabase, set a test user's plan to 'free' and create 10+ completed attempts for the current month. Attempt to start an 11th simulado — expect the error toast: "Limite de 10 simulados mensais atingido."

---

## Notes for reviewers

- **`correct_option` is visible client-side** during the exam. For this MVP this is acceptable — students are practicing, not sitting a monitored exam. Can be moved server-side (Supabase Edge Function) in a future iteration if needed.
- **DB constraints** (unique on `attempt_answers` and `progress_snapshots`) must be applied before the `submitAnswer` and `finishSimulado` calls work correctly. See the prerequisite SQL at the top.
- **`getRandomQuestions` uses client-side shuffle** — true randomisation requires a DB-level `ORDER BY random()` or a Postgres function. For MVP this is acceptable.
