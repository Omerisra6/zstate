import { useSyncExternalStore } from 'react';
import type {
	Context,
	CreateMachineProps,
	DataItem,
	Selector,
	SendPayload,
	States,
	UseContextFunction,
} from './types.ts';

export default function createMachine<
	T extends DataItem,
	C extends Context<T>,
	S extends States<T>,
>({ initialContext, states }: CreateMachineProps<T, C, S>) {
	let context = initialContext;
	const listeners: Array<() => void> = [];

	const subscribe = (listener: () => void): (() => void) => {
		listeners.push(listener);

		return () => {
			listeners.splice(listeners.indexOf(listener), 1);
		};
	};

	const send = ({ eventName, value }: SendPayload<T, S>) => {
		const selectedItem = context.items.find(
			(item) => item.id === context.selected,
		);

		if (!selectedItem) {
			return;
		}

		const currentStatus = selectedItem.status;
		const currentEvent = states[currentStatus];

		if (!currentEvent) {
			return;
		}

		const eventHandler = currentEvent[eventName as string];

		if (!eventHandler) {
			return;
		}

		const updatedItems = context.items.map((item) =>
			item.id === context.selected
				? typeof eventHandler === 'string'
					? { ...item, status: eventHandler }
					: eventHandler(item, value)
				: item,
		);

		context = { ...context, items: updatedItems };

		listeners.forEach((cb) => {
			cb();
		});
	};

	const useMachine: UseContextFunction<T, C> = <R = C>(
		selector: Selector<T, C, R> | undefined,
	) => {
		return useSyncExternalStore(subscribe, () =>
			selector === undefined ? context : selector(context),
		) as R;
	};

	const select = (id: number) => {
		context = { ...context, selected: id };

		listeners.forEach((cb) => {
			cb();
		});
	};

	return { send, useMachine, select };
}
