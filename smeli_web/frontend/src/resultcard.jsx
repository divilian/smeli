import React from "react";
import { useEffect, useState } from "react";


function matchesParam(data, param, originalShow) {
    if (param.type === "branch") {
        return param.choices.every(choice => matchesParam(data, choice));
    }
    if (originalShow === "hidden") {
        return false;
    }

    if (!(param.type in data) || data[param.type] == null) {
        return true;
    }

    const rawValue = param.value;
    const check = data[param.type];

    if (rawValue.includes(">=")) {
        return check >= rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes("<=")) {
        return check <= rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes(">")) {
        return check > rawValue.split(" ", 2)[1];
    }

    if (rawValue.includes("<")) {
        return check < rawValue.split(" ", 2)[1];
    }

    return data[param.type]
        .toString()
        .toLowerCase()
        .includes(rawValue.toLowerCase());
}

export default function ResultCard( {data, index, curParam} ) {

    const [show, setShow] = useState("");

    useEffect(() => {
        if (curParam.type === "reset") {
            setShow("");
            return;
        }

        setShow(matchesParam(data, curParam, show) ? "" : "hidden");
    }, [curParam, data, show]);

    return (
        <div className={`result-card ${show}`}>
            <div class="result-title">
                <span class="title-index">{index + 1}.&nbsp;</span> 
                <span class="title-title">{data.title}&nbsp;</span>
                <span class="title-relevance">
                    [relevance: {data.score}, cites: {data.citation_score}]
                </span>
            </div>
            <div class="result-authors">
                {data.authors.join(", ")} (<span class="result-date">{data.year}</span>)
            </div>
            <div class="result-extra">
                <p><span class="result-extra-key">Type:</span> {data.type}</p>
                <p><span class="result-extra-key">Sources:</span> {data.source}</p>
                <p><span class="result-extra-key">DOI:</span><a href={data.url} target="_blank"> {data.doi}</a></p>
            </div>
        </div>
    );
}
