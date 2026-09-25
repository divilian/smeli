import React from "react";
import { useEffect, useState } from "react";

export default function FilterInput({ newParam }) {

    const params = ["Title", "Authors", "Year", "Identifier", "Score"];
    const [value, setValue] = useState("");
    const [selected, setSelected] = useState(0);

    function handleKeyDown (event) {
        if (event.key === "Enter") {
            newParam({ type: params[selected].toLowerCase(), value });
            console.log({ type: params[selected].toLowerCase(), value });
            setValue( "" );
        }
        else if (event.key === "ArrowUp") {
            if (selected === 0) {
                setSelected(params.length - 1);
            }
            else {
                setSelected(selected - 1);
            }
        }
        else if (event.key === "ArrowDown") {
            if (selected === params.length - 1) {
                setSelected(0);
            }
            else {
                setSelected(selected + 1);
            }
        }
    }

    return (
        <div class="filter-input">
            <select id="filter-type" value={params[selected].toLowerCase()} onChange={(e) => setSelected(e.target.selectedIndex)}>
                {params.map((param) => (
                    <option key={param} value={param.toLowerCase()}>
                        {param}
                    </option>
                ))}
            </select>
            <input autoFocus type="text" placeholder="Enter a Value..." onKeyDown={handleKeyDown} value={value} onChange={ (e) => setValue(e.target.value) }/>
        </div>
    );

}
