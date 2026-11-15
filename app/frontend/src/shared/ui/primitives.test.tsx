import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { Button } from "./button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog";
import { ScrollArea } from "./scroll-area";
import { Separator } from "./separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./tooltip";

beforeAll(() => {
  // Radix popper and scroll-area measure with ResizeObserver, which jsdom lacks.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe(): void {}
      unobserve(): void {}
      disconnect(): void {}
    },
  );
});

describe("shadcn primitives", () => {
  it("Button fires onClick and can render as its child", () => {
    const onClick = vi.fn();
    render(
      <>
        <Button onClick={onClick} variant="outline" size="sm">
          Approve
        </Button>
        <Button asChild>
          <a href="/x">Open</a>
        </Button>
      </>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    expect(onClick).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("data-slot", "button");
  });

  it("Dialog opens from its trigger with a title and description, and closes", () => {
    render(
      <Dialog>
        <DialogTrigger>Review draft</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Work order draft</DialogTitle>
            <DialogDescription>Check the evidence before approving.</DialogDescription>
          </DialogHeader>
          <DialogFooter>footer</DialogFooter>
        </DialogContent>
      </Dialog>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Review draft" }));
    expect(screen.getByRole("dialog", { name: "Work order draft" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("Tabs switch the visible panel", () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Alarms</TabsTrigger>
          <TabsTrigger value="b">Trends</TabsTrigger>
        </TabsList>
        <TabsContent value="a">alarm panel</TabsContent>
        <TabsContent value="b">trend panel</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText("alarm panel")).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole("tab", { name: "Trends" }), { button: 0 });
    expect(screen.getByText("trend panel")).toBeInTheDocument();
  });

  it("Tooltip shows its content when open", () => {
    render(
      <TooltipProvider>
        <Tooltip defaultOpen>
          <TooltipTrigger>Tag</TooltipTrigger>
          <TooltipContent>Compressor K-202</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    );
    expect(screen.getByRole("tooltip")).toHaveTextContent("Compressor K-202");
  });

  it("Separator and ScrollArea render their content", () => {
    render(
      <ScrollArea>
        <p>row</p>
        <Separator orientation="vertical" />
      </ScrollArea>,
    );
    expect(screen.getByText("row")).toBeInTheDocument();
  });
});
