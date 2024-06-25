export type DataItem = {
	id: number;
	status: string;
	props: Record<string, any>;
};

export type Context<T extends DataItem> = {
	selected: number;
	items: T[];
	[key: string]: any;
};

export type EventCallback<T extends DataItem> = (context: T, value?: any) => T;

export type Action<T extends DataItem> = Record<
	string,
	string | EventCallback<T>
>;

export type States<T extends DataItem> = Record<string, Action<T>>;

export type CreateMachineProps<
	T extends DataItem,
	C extends Context<T>,
	S extends States<T>,
> = {
	initialContext: C;
	states: S;
};

export type SendPayload<T extends DataItem, S extends States<T>> = {
	[H in keyof S]: {
		[N in keyof S[H]]: {
			eventName: N;
			value?: S[H][N] extends EventCallback<T>
				? Parameters<S[H][N]>[1]
				: never;
		};
	};
}[keyof S][keyof S[keyof S]];

export type UseContextFunction<
	T extends DataItem,
	C extends Context<T> = Context<T>,
> = <R = C>(selector?: Selector<T, C, R>) => R;

export type Selector<
	T extends DataItem,
	C extends Context<T> = Context<T>,
	R = C,
> = (context: C) => R;
