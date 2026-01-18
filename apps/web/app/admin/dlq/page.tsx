
"use client";

import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, RefreshCw, CheckCircle } from "lucide-react";
import { toast } from "sonner";

// Type definition for FailedTask
interface FailedTask {
    task_id: str;
    task_type: str;
    payload: any;
    error_message: str;
    retry_count: number;
    status: str;
    created_at: str;
    last_retry_at?: str;
}

export default function AdminDLQPage() {
    const [tasks, setTasks] = useState<FailedTask[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchTasks = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/admin/dlq/tasks');
            if (res.ok) {
                const data = await res.json();
                setTasks(data);
            } else {
                toast.error("Failed to fetch DLQ tasks");
            }
        } catch (error) {
            console.error(error);
            toast.error("Connection Error");
        } finally {
            setLoading(false);
        }
    };

    const handleRetry = async (taskId: string) => {
        try {
            const res = await fetch(`http://localhost:8000/admin/dlq/retry/${taskId}`, {
                method: 'POST'
            });
            if (res.ok) {
                toast.success(`Retry initiated for ${taskId}`);
                fetchTasks(); // Refresh list
            } else {
                toast.error("Retry failed");
            }
        } catch (e) {
            toast.error("Retry Error");
        }
    };

    useEffect(() => {
        fetchTasks();
        const interval = setInterval(fetchTasks, 10000); // Poll every 10s
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="container mx-auto p-8 space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Dead Letter Queue</h1>
                    <p className="text-neutral-400">Manage failed autonomous tasks and retries.</p>
                </div>
                <Button onClick={fetchTasks} variant="outline" className="border-neutral-700 text-neutral-300">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh
                </Button>
            </div>

            <div className="grid gap-4">
                {tasks.length === 0 && !loading && (
                    <Card className="bg-neutral-900 border-neutral-800 p-8 text-center text-neutral-500">
                        <CheckCircle className="w-12 h-12 mx-auto mb-4 text-green-500/50" />
                        <p>No failed tasks. System is healthy.</p>
                    </Card>
                )}

                {tasks.map((task) => (
                    <Card key={task.task_id} className="bg-neutral-900 border-neutral-800 border-l-4 border-l-red-500">
                        <CardContent className="pt-6">
                            <div className="flex justify-between items-start">
                                <div className="space-y-1">
                                    <div className="flex items-center gap-2">
                                        <Badge variant="outline" className="text-red-400 border-red-900 bg-red-900/10">
                                            {task.task_type}
                                        </Badge>
                                        <span className="text-neutral-500 text-xs font-mono">{task.task_id}</span>
                                    </div>
                                    <h4 className="font-semibold text-neutral-200 mt-2">Error: {task.error_message}</h4>
                                    <pre className="mt-2 p-2 bg-black/50 rounded text-xs text-neutral-500 font-mono overflow-auto max-w-3xl">
                                        {JSON.stringify(task.payload, null, 2)}
                                    </pre>
                                </div>
                                <div className="flex flex-col items-end gap-2 text-right">
                                    <div className="text-sm text-neutral-400">
                                        Retries: <span className="text-white font-mono">{task.retry_count}</span>
                                    </div>
                                    <div className="text-xs text-neutral-600">
                                        {new Date(task.created_at).toLocaleString()}
                                    </div>
                                    {task.status === "RETRYING" ? (
                                        <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-900">Retrying...</Badge>
                                    ) : (
                                        <Button size="sm" variant="destructive" onClick={() => handleRetry(task.task_id)}>
                                            Retry Task
                                        </Button>
                                    )}
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>
        </div>
    );
}
