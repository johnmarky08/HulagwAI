<?php

namespace App\Services;

use App\Models\Analysis;

/**
 * History for visitors who are not signed in. Nothing is kept in the database
 * once an analysis is claimed: the result (plus a small thumbnail) lives in the
 * encrypted server-side session, tied to the signed session cookie, and
 * disappears with it.
 */
final class GuestHistory
{
    private const HISTORY = 'guest.history';
    private const PENDING = 'guest.pending';

    public function __construct(private readonly FileVault $vault) {}

    /** @return list<string> */
    public function pending(): array
    {
        return array_values((array) session(self::PENDING, []));
    }

    public function addPending(string $id): void
    {
        session()->put(self::PENDING, array_values(array_unique([...$this->pending(), $id])));
    }

    public function removePending(string $id): void
    {
        session()->put(self::PENDING, array_values(array_diff($this->pending(), [$id])));
    }

    /** @return list<array<string,mixed>> newest first */
    public function all(): array
    {
        return array_values((array) session(self::HISTORY, []));
    }

    /** @return array<string,mixed>|null */
    public function find(string $id): ?array
    {
        foreach ($this->all() as $item) {
            if (($item['id'] ?? null) === $id) {
                return $item;
            }
        }

        return null;
    }

    public function remove(string $id): void
    {
        session()->put(self::HISTORY, array_values(array_filter($this->all(), fn ($i) => $i['id'] !== $id)));
    }

    public function clear(): void
    {
        session()->forget([self::HISTORY, self::PENDING]);
    }

    /**
     * Move a finished guest analysis out of the database and into the session.
     *
     * @return array<string,mixed>
     */
    public function claim(Analysis $row): array
    {
        $rec = Records::fromModel($row);
        $rec['thumb_b64'] = $row->thumb_path ? base64_encode($this->vault->get($row->thumb_path, $row->uuid.':thumb')) : null;
        $rec['persisted'] = false;

        $limit = (int) config('hulagwai.guest.history_limit');
        session()->put(self::HISTORY, array_slice([$rec, ...$this->all()], 0, $limit));
        $this->removePending($row->uuid);

        foreach ([$row->file_path, $row->preview_path, $row->thumb_path] as $p) {
            $this->vault->delete($p);
        }
        $row->delete();

        return $rec;
    }
}
